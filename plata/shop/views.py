from decimal import Decimal

from django import forms
from django.contrib import messages
from django.core.urlresolvers import get_callable, reverse
from django.forms.models import inlineformset_factory, modelform_factory
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _

import plata


class Shop(object):
    def __init__(self, product_model, contact_model, order_model):
        self.product_model = product_model
        self.contact_model = contact_model
        self.order_model = order_model
        self.orderitem_model = self.order_model.items.related.model

        plata.register(self)

    @property
    def urls(self):
        return self.get_urls()

    def get_urls(self):
        return self.get_shop_urls() + self.get_admin_urls() + self.get_payment_urls()

    def get_shop_urls(self):
        from django.conf.urls.defaults import patterns, url
        return patterns('',
            url(r'^cart/$', self.cart, name='plata_shop_cart'),
            url(r'^checkout/$', self.checkout, name='plata_shop_checkout'),
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

    def default_currency(self, request):
        return 'CHF'

    def clear_session(self, request):
        for key in ('shop_contact', 'shop_order'):
            if key in request.session:
                del request.session[key]

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
                request.session['shop_order'] = order.pk
                return order

        return None

    def contact_from_request(self, request, create=False):
        # TODO after login, a new contact might be available. what should be done then?
        try:
            return self.contact_model.objects.get(pk=request.session.get('shop_contact'))
        except (ValueError, self.contact_model.DoesNotExist):
            pass

        if request.user.is_authenticated():
            try:
                contact = self.contact_model.objects.get(contactuser__user=request.user)
                request.session['shop_contact'] = contact.pk
                return contact
            except (self.contact_model.DoesNotExist, self.contact_model.MultipleObjectsReturned):
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

            request.session['shop_contact'] = contact.pk
            return contact

        return None

    def get_context(self, request, context):
        instance = RequestContext(request) #, self.get_extra_context(request))
        instance.update(context)
        return instance

    def product_detail(self, request, product, context=None,
            template_name='product/product_detail.html',
            template_form_name='form',
            template_object_name='object'):

        OrderItemForm = self.order_modify_item_form(request, product)

        if request.method == 'POST':
            form = OrderItemForm(request.POST)

            if form.is_valid():
                order = self.order_from_request(request, create=True)

                order.modify_item(
                    form.cleaned_data.get('variation'),
                    form.cleaned_data.get('quantity'),
                    )
                order.recalculate_total()

                messages.success(request, 'Successfully updated cart.')
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
                super(Form, self).__init__(*args, **kwargs)
                for group in product.option_groups.all():
                    self.fields['option_%s' % group.id] = forms.ModelChoiceField(
                        queryset=group.options.all(),
                        label=group.name)

            def clean(self):
                data = super(Form, self).clean()

                options = [data.get('option_%s' % group.id) for group in product.option_groups.all()]

                if all(options):
                    variations = product.variations.all()

                    for group in product.option_groups.all():
                        variations = variations.filter(options=self.cleaned_data.get('option_%s' % group.id))

                    data['variation'] = variations.get()

                return data
        return Form

    def cart(self, request):
        order = self.order_from_request(request, create=False)

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

    def checkout(self, request):
        order = self.order_from_request(request, create=False)

        if not order:
            return HttpResponseRedirect(reverse('plata_shop_cart') + '?empty=1')

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

                return redirect('plata_shop_confirmation')
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

    def confirmation(self, request):
        order = self.order_from_request(request, create=False)

        if not order:
            return HttpResponseRedirect(reverse('plata_shop_cart') + '?empty=1')

        order.recalculate_total()
        payment_modules = self.get_payment_modules()
        payment_module_choices = [(m.__module__, m.name) for m in payment_modules]
        payment_module_dict = dict((m.__module__, m) for m in payment_modules)

        class Form(forms.Form):
            def __init__(self, *args, **kwargs):
                super(Form, self).__init__(*args, **kwargs)
                self.fields['payment_method'] = forms.ChoiceField(
                    label=_('Payment method'),
                    choices=[('', '----------')]+payment_module_choices,
                    )

        if request.method == 'POST':
            form = Form(request.POST)

            if form.is_valid():
                order.update_status(self.order_model.CONFIRMED, 'Confirmation given')

                payment_module = payment_module_dict[form.cleaned_data['payment_method']]
                return payment_module.process_order_confirmed(request, order)
        else:
            form = Form()

        return self.render_confirmation(request, {
            'order': order,
            'form': form,
            })

    def render_confirmation(self, request, context):
        return render_to_response('plata/shop_confirmation.html',
            self.get_context(request, context))

    def order_success(self, request):
        order = self.order_from_request(request)

        if 'shop_order' in request.session:
            del request.session['shop_order']

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

        return render_to_response('plata/shop_order_already_paid.html',
            self.get_context(request, {
                'order': order,
                }))

    def admin_pdf(self, request, order_id):
        order = get_object_or_404(self.order_model, pk=order_id)

        order.shipping_cost = 8 / Decimal('1.076')
        order.shipping_discount = 0
        order.recalculate_total(save=False)

        from pdfdocument.document import PDFDocument, cm, mm
        from pdfdocument.elements import create_stationery_fn, ExampleStationery
        from pdfdocument.utils import pdf_response

        pdf, response = pdf_response('order-%09d' % order.id)
        pdf.init_letter(page_fn=create_stationery_fn(ExampleStationery()))

        pdf.address_head(u'FEINHEIT GmbH - Molkenstrasse 21 - CH-8004 Z\374rich')
        pdf.address(order, 'billing_')
        pdf.next_frame()

        pdf.p(u'%s: %s' % (
            _('Order date'),
            order.confirmed and order.confirmed.strftime('%d.%m.%Y') or _('Not confirmed yet'),
            ))
        pdf.spacer(3*mm)

        pdf.h1('Order %09d' % order.id)
        pdf.hr()

        pdf.table([(
                'Product',
                'Quantity',
                'Unit price',
                'Line item price',
            )]+[
            (
                unicode(item.variation),
                item.quantity,
                u'%.2f' % item.unit_price,
                u'%.2f' % item.discounted_subtotal,
            ) for item in order.items.all()],
            (8*cm, 1*cm, 3*cm, 4.4*cm), pdf.style.tableHead)

        summary_table = [
            ('', ''),
            ('Subtotal', u'%.2f' % order.subtotal),
            ]

        if order.discount:
            summary_table.append(('Discount', u'%.2f' % order.discount))

        if order.shipping:
            summary_table.append(('Shipping', u'%.2f' % order.shipping))

        pdf.table(summary_table, (12*cm, 4.4*cm), pdf.style.table)

        pdf.spacer(1*mm)
        pdf.table([
            ('Total %s' % order.currency, u'%.2f' % order.total),
            ], (12*cm, 4.4*cm), pdf.style.tableHead)

        pdf.generate()
        return response
