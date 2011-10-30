import logging

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import ObjectDoesNotExist
from django.shortcuts import redirect, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _

import plata


logger = logging.getLogger('plata.product.modules.options.views')


class ProductView(object):
    def __init__(self):
        self.shop = plata.shop_instance()

    def product_detail(self, request, product, context=None,
            template_name='product/product_detail.html',
            template_form_name='form',
            template_object_name='object',
            redirect_to='plata_shop_cart'):
        """
        The ``product_detail`` helper provides order item form creation and
        handling on product detail pages. This isn't a complete view - you
        have to implement the product determination yourself. The minimal
        implementation of a product detail view follows::

            import plata

            def my_product_detail_view(request, slug):
                shop = plata.shop_instance()
                product = get_object_or_404(Product, slug=slug)

                return shop.product_detail(request, product)
        """

        OrderItemForm = self.order_modify_item_form(request, product)

        if request.method == 'POST':
            order = self.shop.order_from_request(request, create=True)
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

                return redirect(redirect_to)
        else:
            form = OrderItemForm()

        context = context or {}
        context.update({
            template_form_name: form,
            template_object_name: product,
            })

        return render_to_response(template_name, context,
            context_instance=RequestContext(request))

    def order_modify_item_form(self, request, product):
        """
        Returns a form subclass which is used in ``product_detail`` above
        to handle cart changes on the product detail page.
        """

        class Form(forms.Form):
            quantity = forms.IntegerField(label=_('quantity'), initial=1)

            def __init__(self, *args, **kwargs):
                self.order = kwargs.pop('order', None)

                super(Form, self).__init__(*args, **kwargs)
                for group in product.option_groups.all():
                    self.fields['option_%s' % group.id] = forms.ModelChoiceField(
                        queryset=group.options.filter(
                            variations__is_active=True,
                            variations__product=product).distinct(),
                        label=group.name)

            def clean(self):
                data = super(Form, self).clean()

                options = [data.get('option_%s' % group.id) for group in product.option_groups.all()]

                if all(options):
                    # If we do not have values for all options, the form will not
                    # validate anyway.

                    variations = product.variations.filter(is_active=True)

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
                            orderitem = self.order.items.get(product=variation)
                            old_quantity = orderitem.quantity
                            new_quantity += orderitem.quantity
                        except ObjectDoesNotExist:
                            old_quantity = 0

                    dic = {
                        'stock': variation.items_in_stock,
                        'variation': variation,
                        'quantity': old_quantity,
                        }
                    available = variation.stock_transactions.items_in_stock(variation, # FIXME hardcoded
                        exclude_order=self.order)

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
