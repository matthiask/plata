
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

    def order_from_request(self, request, create=False):
        try:
            return self.order_model.objects.get(pk=request.session.get('shop_order'))
        except (ValueError, self.order_model.DoesNotExist):
            if create:
                order = self.order_model.objects.create()
                request.session['shop_order'] = order.pk
                return order

        return None

    def contact_from_request(self, request, create=False):
        # TODO: check whether user is logged in, reuse information
        try:
            return self.contact_model.objects.get(pk=request.session.get('shop_contact'))
        except (ValueError, self.contact_model.DoesNotExist):
            if create:
                contact = self.contact_model.objects.create()
                request.session['shop_contact'] = contact.pk
                return contact

        return None


    def get_context(self, request, context):
        instance = RequestContext(request) #, self.get_extra_context(request))
        instance.update(context)
        return instance


    def cart(self, request):
        order = self.order_from_request(request, create=False)

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

