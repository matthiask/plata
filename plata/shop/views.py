from django.contrib import messages
from django.core.urlresolvers import reverse
from django.forms.models import inlineformset_factory, modelform_factory
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render_to_response
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

    def get_urls(self):
        return self.get_product_urls() + self.get_shop_urls()

    def get_product_urls(self):
        from django.conf.urls.defaults import patterns, url

        product_dict = {
            'queryset': self.product_model.objects.all(),
            }

        return patterns('django.views.generic',
            url(r'^$', lambda request: redirect('plata_product_list')),
            url(r'^products/$', 'list_detail.object_list', product_dict, name='plata_product_list'),
            url(r'^products/(?P<object_id>\d+)/$', 'list_detail.object_detail', product_dict, name='plata_product_detail'),
            )

    def get_shop_urls(self):
        from django.conf.urls.defaults import patterns, url
        return patterns('',
            url(r'^api/order_modify_item/$', self.order_modify_item, name='plata_order_modify_item'),
            url(r'^cart/$', self.cart, name='plata_shop_cart'),
            url(r'^checkout/$', self.checkout, name='plata_shop_checkout'),
            url(r'^confirmation/$', self.confirmation, name='plata_shop_confirmation'),
            )

    @property
    def urls(self):
        return self.get_urls()

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
        try:
            return self.contact_model.objects.get(pk=request.session.get('shop_contact'))
        except (ValueError, self.contact_model.DoesNotExist):
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
                        'user': request.user,
                    })

                contact = self.contact_model.objects.create(**initial)
                request.session['shop_contact'] = contact.pk
                return contact

        return None

    def get_context(self, request, context):
        instance = RequestContext(request) #, self.get_extra_context(request))
        instance.update(context)
        return instance

    def order_modify_item(self, request):
        order = self.order_from_request(request, create=True)
        product = self.product_model.objects.get(pk=request.POST.get('product'))

        order.modify_item(product, int(request.POST.get('quantity')))
        order.recalculate_total()

        messages.success(request, 'Successfully updated cart.')
        return HttpResponseRedirect(product.get_absolute_url())

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
                formset.save()
                order.recalculate_total()

                if any(form.changed_data for form in formset.forms):
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

    def checkout(self, request):
        order = self.order_from_request(request, create=False)

        if not order:
            return HttpResponseRedirect(reverse('plata_shop_cart') + '?empty=1')

        ContactForm = modelform_factory(self.contact_model, exclude=('user', 'created', 'notes'))
        OrderForm = modelform_factory(self.order_model, fields=('notes',))

        if request.method == 'POST':
            c_form = ContactForm(request.POST, instance=order.contact)
            o_form = OrderForm(request.POST, instance=order)

            if c_form.is_valid() and o_form.is_valid():
                c_form.save()
                order = o_form.save()
                order.copy_address()
                order.save()

                return redirect('plata_shop_confirmation')
        else:
            c_form = ContactForm(instance=order.contact)
            o_form = OrderForm(instance=order)

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

        return self.render_confirmation(request, {'order': order})

    def render_confirmation(self, request, context):
        return render_to_response('plata/shop_confirmation.html',
            self.get_context(request, context))
