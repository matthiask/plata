from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import ObjectDoesNotExist
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.views.generic import  list_detail

import plata
from plata.discount.models import Discount
from plata.shop.views import Shop
from plata.shop.models import Contact, Order

from simple.models import Product


shop = Shop(Contact, Order, Discount)


def product_list(request):
    return list_detail.object_list(request,
        queryset=Product.objects.active(),
        paginate_by=9,
        template_name='product/product_list.html',
        )


class OrderItemForm(forms.Form):
    quantity = forms.IntegerField(label=_('quantity'), initial=1)

    def __init__(self, *args, **kwargs):
        self.order = kwargs.pop('order', None)
        self.product = kwargs.pop('product')
        super(OrderItemForm, self).__init__(*args, **kwargs)

    def clean(self):
        data = super(OrderItemForm, self).clean()

        try:
            data['price'] = self.product.get_price(currency=self.order.currency)
        except ObjectDoesNotExist:
            raise forms.ValidationError(_('Price could not be determined.'))

        return data


def product_detail(request, object_id):
    shop = plata.shop_instance()
    product = get_object_or_404(Product.objects.active(), pk=object_id)

    if request.method == 'POST':
        order = shop.order_from_request(request, create=True)
        form = OrderItemForm(request.POST, order=order, product=product)

        if form.is_valid():
            try:
                order.modify_item(product, form.cleaned_data.get('quantity'))
                messages.success(request, _('The cart has been updated.'))
            except ValidationError, e:
                if e.code == 'order_sealed':
                    [messages.error(request, msg) for msg in e.messages]
                else:
                    raise

            return redirect('plata_shop_cart')
    else:
        form = OrderItemForm(product=product)

    return render_to_response('product/product_detail.html', {
        'object': product,
        'form': form,
        }, context_instance=RequestContext(request))
