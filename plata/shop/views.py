from decimal import Decimal
from functools import wraps

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.urlresolvers import get_callable, reverse
from django.db.models import ObjectDoesNotExist
from django.forms.models import inlineformset_factory, modelform_factory
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _, ungettext

import plata


def cart_not_empty(order, request, **kwargs):
    # Redirect to cart if later in checkout process and cart empty
    if not order or not order.items.count():
        messages.warning(request, _('Cart is empty.'))
        return HttpResponseRedirect(reverse('plata_shop_cart') + '?empty=1')

def order_confirmed(order, request, **kwargs):
    # Redirect to confirmation or already paid view if the order is already confirmed
    if order and order.is_confirmed():
        if order.is_paid():
            return redirect('plata_order_already_paid')
        messages.warning(request,
            _('You have already confirmed this order earlier, but it is not fully paid for yet.'))
        return HttpResponseRedirect(reverse('plata_shop_confirmation') + '?confirmed=1')

def insufficient_stock(order, request, **kwargs):
    if request.method != 'GET':
        return

    try:
        order.validate(stock=True)
    except ValidationError, e:
        if e.code == 'insufficient_stock':
            return HttpResponseRedirect(reverse('plata_shop_cart') + '?insufficient_stock=1')
        raise

def checkout_process_decorator(*checks):
    def _dec(fn):
        def _fn(self, request, *args, **kwargs):
            order = self.order_from_request(request, create=False)

            for check in checks:
                r = check(order=order, shop=self, request=request)
                if r: return r

            return fn(self, request, order=order, *args, **kwargs)
        return wraps(fn)(_fn)
    return _dec


class Shop(object):
    """
    Plata's view and shop processing logic is contained inside this class.

    Shop needs a few model classes with relations between them:

    - Product class with variations, option groups, options and prices
    - Contact model with a ContactUser class linking to Django's auth.user
    - Order model with order items and an applied discount model
    - Discount model
    """

    def __init__(self, product_model, contact_model, order_model, discount_model):
        self.product_model = product_model
        self.contact_model = contact_model
        self.order_model = order_model
        self.orderitem_model = self.order_model.items.related.model
        self.discount_model = discount_model

        # Globally register the instance so that it can be accessed from
        # everywhere using plata.shop_instance()
        plata.register(self)

    @property
    def urls(self):
        return self.get_urls()

    def get_urls(self):
        return self.get_shop_urls() + self.get_payment_urls()

    def get_shop_urls(self):
        from django.conf.urls.defaults import patterns, url
        return patterns('',
            url(r'^cart/$', self.cart, name='plata_shop_cart'),
            url(r'^checkout/$', self.checkout, name='plata_shop_checkout'),
            url(r'^discounts/$', self.discounts, name='plata_shop_discounts'),
            url(r'^confirmation/$', self.confirmation, name='plata_shop_confirmation'),

            url(r'^order/success/$', self.order_success, name='plata_order_success'),
            url(r'^order/payment_failure/$', self.order_payment_failure, name='plata_order_payment_failure'),

            url(r'^order/already_paid/$', self.order_already_paid, name='plata_order_already_paid'),
            )

    def get_admin_urls(self):
        from django.conf.urls.defaults import patterns, url
        return patterns('',
            url(r'^pdf/(?P<order_id>\d+)/$', self.admin_pdf, name='plata_admin_pdf'),
            )

    def get_payment_urls(self):
        from django.conf.urls.defaults import patterns, url, include
        urls = [url(r'', include(module.urls)) for module in self.get_payment_modules()]
        return patterns('', *urls)

    def get_payment_modules(self):
        return [get_callable(module)(self) for module in plata.settings.PLATA_PAYMENT_MODULES]

    def default_currency(self, request=None):
        return 'CHF'

    def set_order_on_request(self, request, order):
        if order:
            request.session['shop_order'] = order.pk
        elif 'shop_order' in request.session:
            del request.session['shop_order']

    def set_contact_on_request(self, request, contact):
        if contact:
            request.session['shop_contact'] = contact.pk
        elif 'shop_contact' in request.session:
            del request.session['shop_contact']

    def order_from_request(self, request, create=False):
        try:
            return self.order_model.objects.get(pk=request.session.get('shop_order'))
        except (ValueError, self.order_model.DoesNotExist):
            if create:
                contact = self.contact_from_request(request, create)
                order = self.order_model.objects.create(
                    contact=contact,
                    currency=contact.currency,
                    )
                self.set_order_on_request(request, order)
                return order

        return None

    def contact_from_request(self, request, create=False):
        # TODO after login, a new contact might be available. what should be done then?
        try:
            return self.contact_model.objects.get(pk=request.session.get('shop_contact'))
        except (ValueError, self.contact_model.DoesNotExist):
            pass

        if request.user.is_authenticated():
            # Try finding a contact which is already linked with the currently
            # authenticated user
            try:
                contact = self.contact_model.objects.get(contactuser__user=request.user)
                self.set_contact_on_request(request, contact)
                return contact
            except self.contact_model.DoesNotExist:
                pass

        if create:
            initial = {
                'shipping_same_as_billing': True,
                'currency': self.default_currency(request),
                }

            if request.user.is_authenticated():
                initial.update({
                    'billing_first_name': request.user.first_name,
                    'billing_last_name': request.user.last_name,
                    'email': request.user.email,
                })

            contact = self.contact_model.objects.create(**initial)

            if request.user.is_authenticated():
                self.contact_model.contactuser.related.model.objects.create(
                    contact=contact,
                    user=request.user)

            self.set_contact_on_request(request, contact)
            return contact

        return None

    def get_context(self, request, context):
        instance = RequestContext(request)
        instance.update(context)
        return instance

    def product_detail(self, request, product, context=None,
            template_name='product/product_detail.html',
            template_form_name='form',
            template_object_name='object'):

        OrderItemForm = self.order_modify_item_form(request, product)

        if request.method == 'POST':
            order = self.order_from_request(request, create=True)
            form = OrderItemForm(request.POST, order=order)

            if form.is_valid():
                try:
                    order.modify_item(
                        form.cleaned_data.get('variation'),
                        form.cleaned_data.get('quantity'),
                        )
                    messages.success(request, _('The cart has been updated.'))
                except ValidationError, e:
                    if e.code == 'order_sealed':
                        [messages.error(request, msg) for msg in e.messages]
                    else:
                        raise

                order.recalculate_total()

                return HttpResponseRedirect('.')
        else:
            form = OrderItemForm()

        context = context or {}
        context.update({
            template_form_name: form,
            template_object_name: product,
            })

        return render_to_response(template_name, self.get_context(request, context))

    def order_modify_item_form(self, request, product):
        class Form(forms.Form):
            quantity = forms.IntegerField(label=_('quantity'), initial=1)

            def __init__(self, *args, **kwargs):
                self.order = kwargs.pop('order', None)

                super(Form, self).__init__(*args, **kwargs)
                for group in product.option_groups.all():
                    self.fields['option_%s' % group.id] = forms.ModelChoiceField(
                        queryset=group.options.filter(variations__product=product).distinct(),
                        label=group.name)

            def clean(self):
                data = super(Form, self).clean()

                options = [data.get('option_%s' % group.id) for group in product.option_groups.all()]

                if all(options):
                    # If we do not have values for all options, the form will not
                    # validate anyway.

                    variations = product.variations.all()

                    for group in product.option_groups.all():
                        variations = variations.filter(options=self.cleaned_data.get('option_%s' % group.id))

                    try:
                        data['variation'] = variations.get()
                    except ObjectDoesNotExist:
                        # TODO: This is quite a serious error
                        raise forms.ValidationError(_('The requested product does not exist.'))

                quantity = new_quantity = data.get('quantity')
                variation = data.get('variation')

                if quantity and variation:
                    if self.order:
                        try:
                            orderitem = self.order.items.get(variation=variation)
                            old_quantity = orderitem.quantity
                            new_quantity += orderitem.quantity
                        except ObjectDoesNotExist:
                            old_quantity = 0

                    if new_quantity > variation.items_in_stock:
                        self._errors['quantity'] = self.error_class([
                            _('Only %(stock)s items for %(variation)s available; you already have %(quantity)s in your order.') % {
                                'stock': variation.items_in_stock,
                                'variation': variation,
                                'quantity': old_quantity,
                                }])

                try:
                    data['price'] = product.get_price(currency=self.order.currency)
                except ObjectDoesNotExist:
                    raise forms.ValidationError(_('Price could not be determined.'))

                return data
        return Form

    @checkout_process_decorator(order_confirmed)
    def cart(self, request, order):
        if not order:
            return self.render_cart_empty(request, {})

        OrderItemFormset = inlineformset_factory(
            self.order_model,
            self.orderitem_model,
            extra=0,
            fields=('quantity',),
            )

        if request.method == 'POST':
            formset = OrderItemFormset(request.POST, instance=order)

            if formset.is_valid():
                changed = False

                # We cannot directly save the formset, because the additional
                # checks in modify_item must be performed.

                try:
                    for form in formset.forms:
                        if formset.can_delete and formset._should_delete_form(form):
                            order.modify_item(form.instance.variation,
                                absolute=0,
                                recalculate=False)
                            changed = True
                        elif form.has_changed():
                            order.modify_item(form.instance.variation,
                                absolute=form.cleaned_data['quantity'],
                                recalculate=False)
                            changed = True

                    if changed:
                        order.recalculate_total()
                        messages.success(request, _('The cart has been updated.'))

                except ValidationError, e:
                    if e.code == 'order_sealed':
                        [messages.error(request, msg) for msg in e.messages]
                    else:
                        raise

                if 'checkout' in request.POST:
                    return redirect('plata_shop_checkout')
                return HttpResponseRedirect('.')
        else:
            formset = OrderItemFormset(instance=order)

        return self.render_cart(request, {
            'order': order,
            'orderitemformset': formset,
            'empty': request.GET.get('empty', False), # Whether the cart is empty.
                                                      # Flag gets set by checkout view.
            })

    def render_cart_empty(self, request, context):
        context.update({'empty': True})

        return render_to_response('plata/shop_cart.html',
            self.get_context(request, context))

    def render_cart(self, request, context):
        return render_to_response('plata/shop_cart.html',
            self.get_context(request, context))

    def checkout_contact_form(self, request, order):
        if not hasattr(self, '_checkout_contact_form_cache'):
            REQUIRED_ADDRESS_FIELDS = self.order_model.ADDRESS_FIELDS[:]
            REQUIRED_ADDRESS_FIELDS.remove('company')

            class ContactForm(forms.ModelForm):
                class Meta:
                    model = self.contact_model
                    exclude = ('user', 'created', 'notes', 'currency')

                def clean(self):
                    if not self.cleaned_data.get('shipping_same_as_billing'):
                        for f in REQUIRED_ADDRESS_FIELDS:
                            field = 'shipping_%s' % f
                            if not self.cleaned_data.get(field):
                                self._errors[field] = self.error_class([
                                    _('This field is required.')])
                    return self.cleaned_data

            for f in REQUIRED_ADDRESS_FIELDS:
                ContactForm.base_fields['billing_%s' % f].required = True
            self._checkout_contact_form_cache = ContactForm
        return self._checkout_contact_form_cache

    def checkout_order_form(self, request, order):
        return modelform_factory(self.order_model, fields=('notes',))

    @checkout_process_decorator(cart_not_empty, order_confirmed, insufficient_stock)
    def checkout(self, request, order):
        ContactForm = self.checkout_contact_form(request, order)
        OrderForm = self.checkout_order_form(request, order)

        if request.method == 'POST':
            c_form = ContactForm(request.POST, prefix='contact', instance=order.contact)
            o_form = OrderForm(request.POST, prefix='order', instance=order)

            if c_form.is_valid() and o_form.is_valid():
                c_form.save()
                order = o_form.save()
                order.copy_address()
                order.save()

                if order.status < self.order_model.CHECKOUT:
                    order.update_status(self.order_model.CHECKOUT, 'Checkout completed')

                return redirect('plata_shop_discounts')
        else:
            c_form = ContactForm(instance=order.contact, prefix='contact')
            o_form = OrderForm(instance=order, prefix='order')

        return self.render_checkout(request, {
            'order': order,
            'contactform': c_form,
            'orderform': o_form,
            })

    def render_checkout(self, request, context):
        return render_to_response('plata/shop_checkout.html',
            self.get_context(request, context))

    def discount_form(self, request, order):
        if not hasattr(self, '_discount_form_cache'):
            class DiscountForm(forms.Form):
                code = forms.CharField(label=_('code'), max_length=30, required=False)

                def __init__(self, *args, **kwargs):
                    self.order = kwargs.pop('order')
                    super(DiscountForm, self).__init__(*args, **kwargs)

                def clean_code(self):
                    code = self.cleaned_data.get('code')
                    if not code:
                        return self.cleaned_data

                    shop = plata.shop_instance()

                    try:
                        discount = shop.discount_model.objects.get(code=code)
                    except shop.discount_model.DoesNotExist:
                        raise forms.ValidationError(_('This code does not validate'))

                    discount.validate(self.order)
                    self.cleaned_data['discount'] = discount
                    return code
            self._discount_form_cache = DiscountForm
        return self._discount_form_cache

    @checkout_process_decorator(cart_not_empty, order_confirmed, insufficient_stock)
    def discounts(self, request, order):
        DiscountForm = self.discount_form(request, order)

        if request.method == 'POST':
            form = DiscountForm(request.POST, order=order)

            if form.is_valid():
                if 'discount' in form.cleaned_data:
                    order.add_discount(form.cleaned_data['discount'])

                if 'proceed' in request.POST:
                    return redirect('plata_shop_confirmation')
                return HttpResponseRedirect('.')
        else:
            form = DiscountForm(order=order)

        order.recalculate_total()

        return self.render_discounts(request, {
            'order': order,
            'form': form,
            })

    def render_discounts(self, request, context):
        return render_to_response('plata/shop_discounts.html',
            self.get_context(request, context))

    @checkout_process_decorator(cart_not_empty, insufficient_stock)
    def confirmation(self, request, order):
        order.recalculate_total()
        payment_modules = self.get_payment_modules()
        payment_module_choices = [(m.__module__, m.name) for m in payment_modules]
        payment_module_dict = dict((m.__module__, m) for m in payment_modules)

        class Form(forms.Form):
            def __init__(self, *args, **kwargs):
                self.order = kwargs.pop('order')

                super(Form, self).__init__(*args, **kwargs)
                self.fields['payment_method'] = forms.ChoiceField(
                    label=_('Payment method'),
                    choices=[('', '----------')]+payment_module_choices,
                    )

            def clean(self):
                data = super(Form, self).clean()
                order.validate(all=True)
                return data

        if request.method == 'POST':
            form = Form(request.POST, order=order)

            if form.is_valid():
                order.update_status(self.order_model.CONFIRMED, 'Confirmation given')

                payment_module = payment_module_dict[form.cleaned_data['payment_method']]
                return payment_module.process_order_confirmed(request, order)
        else:
            form = Form(order=order)

        return self.render_confirmation(request, {
            'order': order,
            'form': form,
            'confirmed': request.GET.get('confirmed', False), # Whether the order had
                                                              # already been confirmed
            })

    def render_confirmation(self, request, context):
        return render_to_response('plata/shop_confirmation.html',
            self.get_context(request, context))

    def order_success(self, request):
        order = self.order_from_request(request)
        self.set_order_on_request(request, order=None)

        return render_to_response('plata/shop_order_success.html',
            self.get_context(request, {
                'order': order,
                }))

    def order_payment_failure(self, request):
        order = self.order_from_request(request)

        return render_to_response('plata/shop_order_payment_failure.html',
            self.get_context(request, {
                'order': order,
                }))

    def order_already_paid(self, request):
        order = self.order_from_request(request)
        self.set_order_on_request(request, order=None)

        return render_to_response('plata/shop_order_already_paid.html',
            self.get_context(request, {
                'order': order,
                }))
