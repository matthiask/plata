from django.core.urlresolvers import reverse
from django.forms.models import inlineformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext


class Shop(object):
    def __init__(self, product_model, contact_model, order_model):
        self.product_model = product_model
        self.contact_model = contact_model
        self.order_model = order_model
        self.orderitem_model = self.order_model.items.related.model

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url

        return patterns('',
            url(r'^cart/$', self.cart, name='plata_shop_cart'),
            url(r'^checkout/$', self.checkout, name='plata_shop_checkout'),
            url(r'^confirmation/$', self.confirmation, name='plata_shop_confirmation'),
            )

    @property
    def urls(self):
        return self.get_urls()

    def default_currency(self, request):
        return 'CHF'

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

    def cart(self, request):
        order = self.order_from_request(request, create=False)

        if not order:
            return self.render_cart_empty(request, {})

        OrderItemFormset = inlineformset_factory(
            self.order_model,
            self.orderitem_model,
            extra=0)

        if request.method == 'POST':
            formset = OrderItemFormset(request.POST, instance=order)

            if formset.is_valid():
                formset.save()

                messages.success(request, _('The cart has been updated.'))

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

        OrderForm = modelform_factory(self.order_model)

        if request.method == 'POST':
            form = OrderForm(request.POST, instance=order)

            if form.is_valid():
                form.save()

                return redirect('plata_shop_confirmation')
        else:
            form = OrderForm(instance=order)

        return self.render_checkout(request, {
            'order': order,
            'orderform': form,
            })

    def render_checkout(self, request, context):
        return render_to_response('plata/shop_checkout.html',
            self.get_context(request, context))

    def confirmation(self, request):
        pass
