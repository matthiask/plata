from decimal import Decimal
from functools import wraps
import logging

from django import forms
from django.contrib import auth, messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import get_callable, reverse
from django.db.models import ObjectDoesNotExist
from django.forms.models import inlineformset_factory, modelform_factory
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _, ungettext

import plata
from plata.shop import signals


logger = logging.getLogger('plata.shop.views')


def cart_not_empty(order, request, **kwargs):
    # Redirect to cart if later in checkout process and cart empty
    if not order or not order.items.count():
        messages.warning(request, _('Cart is empty.'))
        return HttpResponseRedirect(reverse('plata_shop_cart'))

def order_confirmed(order, request, **kwargs):
    # Redirect to confirmation or already paid view if the order is already confirmed
    if order and order.is_confirmed():
        if order.is_paid():
            return redirect('plata_order_success')
        messages.warning(request,
            _('You have already confirmed this order earlier, but it is not fully paid for yet.'))
        return HttpResponseRedirect(reverse('plata_shop_confirmation') + '?confirmed=1')

def insufficient_stock(order, request, **kwargs):
    if request.method != 'GET':
        return

    try:
        order.validate(order.VALIDATE_CART)
    except ValidationError, e:
        for message in e.messages:
            messages.error(request, message)
        return HttpResponseRedirect(reverse('plata_shop_cart'))

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
    - Contact model linking to Django's auth.user
    - Order model with order items and an applied discount model
    - Discount model
    - Default currency for the shop (if you do not override default_currency
      in your own Shop subclass)
    """

    def __init__(self, product_model, contact_model, order_model, discount_model,
            default_currency=None):
        self.product_model = product_model
        self.contact_model = contact_model
        self.order_model = order_model
        self.orderitem_model = self.order_model.items.related.model
        self.discount_model = discount_model
        self._default_currency = default_currency

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
            url(r'^order/new/$', self.order_new, name='plata_order_new'),
            )

    def get_payment_urls(self):
        from django.conf.urls.defaults import patterns, url, include
        urls = [url(r'', include(module.urls)) for module in self.get_payment_modules()]
        return patterns('', *urls)

    def get_payment_modules(self):
        return [get_callable(module)(self) for module in plata.settings.PLATA_PAYMENT_MODULES]

    def default_currency(self, request=None):
        return self._default_currency or plata.settings.CURRENCIES[0]

    def set_order_on_request(self, request, order):
        if order:
            request.session['shop_order'] = order.pk
        elif 'shop_order' in request.session:
            del request.session['shop_order']

    def order_from_request(self, request, create=False):
        try:
            order_pk = request.session.get('shop_order')
            if order_pk is None:
                raise ValueError("no order in session")
            return self.order_model.objects.get(pk=order_pk)
        except (ValueError, self.order_model.DoesNotExist):
            if create:
                contact = self.contact_from_user(request.user)
                currency = contact and contact.currency or self.default_currency(request)

                order = self.order_model.objects.create(
                    contact=contact,
                    currency=currency,
                    )
                self.set_order_on_request(request, order)
                return order

        return None

    def contact_from_user(self, user):
        if not user.is_authenticated():
            return None

        try:
            return self.contact_model.objects.get(user=user)
        except self.contact_model.DoesNotExist:
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
                        logger.warn('Product variation of %s with options %s does not exist' % (
                            product, options))
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

                    dic = {
                        'stock': variation.items_in_stock,
                        'variation': variation,
                        'quantity': old_quantity,
                        }
                    available = variation.available(exclude_order=self.order)

                    if new_quantity > available:
                        if not available:
                            self._errors['quantity'] = self.error_class([
                                _('No items of %(variation)s on stock.') % dic])
                        elif old_quantity:
                            self._errors['quantity'] = self.error_class([
                                _('Only %(stock)s items for %(variation)s available; you already have %(quantity)s in your order.') % dic])
                        else:
                            self._errors['quantity'] = self.error_class([
                                _('Only %(stock)s items for %(variation)s available.') % dic])

                try:
                    data['price'] = product.get_price(currency=self.order.currency)
                except ObjectDoesNotExist:
                    raise forms.ValidationError(_('Price could not be determined.'))

                return data
        return Form

    @checkout_process_decorator(order_confirmed)
    def cart(self, request, order):
        if not order or not order.items.count():
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

                if 'checkout' in request.POST:
                    return redirect('plata_shop_checkout')
                return HttpResponseRedirect('.')
        else:
            formset = OrderItemFormset(instance=order)

        return self.render_cart(request, {
            'order': order,
            'orderitemformset': formset,
            })

    def render_cart_empty(self, request, context):
        context.update({'empty': True})

        return render_to_response('plata/shop_cart.html',
            self.get_context(request, context))

    def render_cart(self, request, context):
        return render_to_response('plata/shop_cart.html',
            self.get_context(request, context))

    def checkout_form(self, request, order):
        REQUIRED_ADDRESS_FIELDS = self.order_model.ADDRESS_FIELDS[:]
        REQUIRED_ADDRESS_FIELDS.remove('company')

        class OrderForm(forms.ModelForm):
            class Meta:
                fields = ['notes', 'email', 'shipping_same_as_billing']
                fields.extend('billing_%s' % f for f in self.order_model.ADDRESS_FIELDS)
                fields.extend('shipping_%s' % f for f in self.order_model.ADDRESS_FIELDS)
                model = self.order_model

            def __init__(self, *args, **kwargs):
                self.request = kwargs.pop('request')
                self.contact = kwargs.pop('contact')

                super(OrderForm, self).__init__(*args, **kwargs)

                if not self.contact:
                    self.fields['create_account'] = forms.BooleanField(
                        label=_('create account'),
                        required=False, initial=True)

            def clean(self):
                data = self.cleaned_data

                if not data.get('shipping_same_as_billing'):
                    for f in REQUIRED_ADDRESS_FIELDS:
                        field = 'shipping_%s' % f
                        if not data.get(field):
                            self._errors[field] = self.error_class([
                                _('This field is required.')])

                email = data.get('email')
                create_account = data.get('create_account')

                if email:
                    users = list(User.objects.filter(email=email))

                    if users:
                        if self.request.user not in users:
                            if self.request.user.is_authenticated():
                                self._errors['email'] = self.error_class([
                                    _('This e-mail address belongs to a different account.')])
                            else:
                                self._errors['email'] = self.error_class([
                                    _('This e-mail address might belong to you, but we cannot know for sure because you are not authenticated yet.')])

                            # Clear e-mail address so that further processing is aborted
                            email = None

                if email and create_account and not self.contact and not self._errors:
                    password = None
                    if not self.request.user.is_authenticated():
                        password = User.objects.make_random_password()
                        user = User.objects.create_user(email, email, password)
                        user = auth.authenticate(username=email, password=password)
                        auth.login(self.request, user)
                    else:
                        user = self.request.user

                    shop = plata.shop_instance()
                    contact = shop.contact_model(
                        user=user,
                        currency=self.instance.currency)

                    for k, v in data.items():
                        if k.startswith('shipping_') or k.startswith('billing_'):
                            setattr(contact, k, v)
                    contact.save()
                    self.instance.contact = contact

                    signals.contact_created.send(sender=self, user=user,
                        contact=contact, password=password)
                elif self.contact:
                    self.instance.contact = self.contact

                return data

        return OrderForm

    @checkout_process_decorator(cart_not_empty, order_confirmed, insufficient_stock)
    def checkout(self, request, order):
        if not request.user.is_authenticated():
            if request.method == 'POST' and '_login' in request.POST:
                loginform = AuthenticationForm(data=request.POST, prefix='login')

                if loginform.is_valid():
                    user = loginform.get_user()
                    auth.login(request, user)

                    order.contact = self.contact_from_user(user)
                    order.save()

                    return HttpResponseRedirect('.')
            else:
                loginform = AuthenticationForm(prefix='login')
        else:
            loginform = None

        if order.status < self.order_model.CHECKOUT:
            order.update_status(self.order_model.CHECKOUT, 'Checkout process started')

        OrderForm = self.checkout_form(request, order)
        contact = self.contact_from_user(request.user)

        initial = {}
        if contact:
            initial['email'] = contact.user.email
            initial['shipping_same_as_billing'] = contact.shipping_same_as_billing
            for f in contact.ADDRESS_FIELDS:
                initial['billing_%s' % f] = getattr(contact, 'billing_%s' % f)
                initial['shipping_%s' % f] = getattr(contact, 'shipping_%s' % f)

        orderform_kwargs = {
            'prefix': 'order',
            'instance': order,
            'request': request,
            'contact': contact,
            'initial': initial,
            }

        if request.method == 'POST' and '_checkout' in request.POST:
            orderform = OrderForm(request.POST, **orderform_kwargs)

            if orderform.is_valid():
                order = orderform.save()

                return redirect('plata_shop_discounts')
        else:
            orderform = OrderForm(**orderform_kwargs)

        return self.render_checkout(request, {
            'order': order,
            'loginform': loginform,
            'orderform': orderform,
            })

    def render_checkout(self, request, context):
        return render_to_response('plata/shop_checkout.html',
            self.get_context(request, context))

    def discounts_form(self, request, order):
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
        return DiscountForm

    @checkout_process_decorator(cart_not_empty, order_confirmed, insufficient_stock)
    def discounts(self, request, order):
        DiscountForm = self.discounts_form(request, order)

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

    def confirmation_form(self, request, order):
        class ConfirmationForm(forms.Form):
            terms_and_conditions = forms.BooleanField(
                label=_('I accept the terms and conditions.'),
                required=True)

            def __init__(self, *args, **kwargs):
                self.order = kwargs.pop('order')

                super(ConfirmationForm, self).__init__(*args, **kwargs)
                payment_module_choices = [(m.__module__, m.name) for m in \
                    plata.shop_instance().get_payment_modules()]
                self.fields['payment_method'] = forms.ChoiceField(
                    label=_('Payment method'),
                    choices=[('', '----------')]+payment_module_choices,
                    )

            def clean(self):
                data = super(ConfirmationForm, self).clean()
                order.validate(order.VALIDATE_ALL)
                return data
        return ConfirmationForm

    @checkout_process_decorator(cart_not_empty, insufficient_stock)
    def confirmation(self, request, order):
        order.recalculate_total()
        payment_module_dict = dict((m.__module__, m) for m in self.get_payment_modules())

        ConfirmationForm = self.confirmation_form(request, order)

        if request.method == 'POST':
            form = ConfirmationForm(request.POST, order=order)

            if form.is_valid():
                order.update_status(self.order_model.CONFIRMED, 'Confirmation given')
                signals.order_confirmed.send(sender=self, order=order)
                payment_module = payment_module_dict[form.cleaned_data['payment_method']]
                return payment_module.process_order_confirmed(request, order)
        else:
            form = ConfirmationForm(order=order)

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

        if not order:
            return self.order_new(request)

        return render_to_response('plata/shop_order_success.html',
            self.get_context(request, {
                'order': order,
                }))

    def order_payment_failure(self, request):
        order = self.order_from_request(request)

        logger.warn('Order payment failure for %s' % order)

        return render_to_response('plata/shop_order_payment_failure.html',
            self.get_context(request, {
                'order': order,
                }))

    def order_new(self, request):
        self.set_order_on_request(request, order=None)

        next = request.GET.get('next')
        if next:
            return HttpResponseRedirect(next)

        return HttpResponseRedirect('/')
