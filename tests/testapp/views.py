from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import ugettext_lazy as _
from django.views import generic

import plata
from testapp.models import Product


product_list = generic.ListView.as_view(
    queryset=Product.objects.all(),
    paginate_by=10,
    template_name='product/product_list.html',
    )


class OrderItemForm(forms.Form):
    quantity = forms.IntegerField(label=_('quantity'), initial=1,
        min_value=1, max_value=100)


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        form = OrderItemForm(request.POST)

        if form.is_valid():
            shop = plata.shop_instance()
            order = shop.order_from_request(request, create=True)
            try:
                order.modify_item(product, form.cleaned_data.get('quantity'))
                messages.success(request, _('The cart has been updated.'))
            except forms.ValidationError as e:
                if e.code == 'order_sealed':
                    [messages.error(request, msg) for msg in e.messages]
                else:
                    raise

            return redirect('plata_shop_cart')
    else:
        form = OrderItemForm()

    return render(request, 'product/product_detail.html', {
        'object': product,
        'form': form,
        })
