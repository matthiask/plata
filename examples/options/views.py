from django.shortcuts import get_object_or_404
from django.views.generic import  list_detail

import plata
from plata.discount.models import Discount
from plata.product.modules.options.models import Product
from plata.product.modules.options.views import ProductView
from plata.shop.views import Shop
from plata.shop.models import Contact, Order


shop = Shop(Contact, Order, Discount)


def product_list(request):
    return list_detail.object_list(request,
        queryset=Product.objects.active(),
        paginate_by=9,
        template_name='product/product_list.html',
        )


def product_detail(request, object_id):
    product = get_object_or_404(Product.objects.active(), pk=object_id)

    view = ProductView()
    return view.product_detail(request, product)
