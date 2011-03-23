from django.shortcuts import get_object_or_404
from django.views.generic import  list_detail

import plata
from plata.product.feincms.models import CMSProduct
from plata.shop.views import Shop
from plata.shop.models import Contact, Order, Discount


shop = Shop(CMSProduct, Contact, Order, Discount)


def product_list(request):
    return list_detail.object_list(request,
        queryset=CMSProduct.objects.active(),
        paginate_by=9,
        template_name='product/product_list.html',
        )


def product_detail(request, object_id):
    product = get_object_or_404(CMSProduct.objects.active(), pk=object_id)

    return shop.product_detail(request, product)
