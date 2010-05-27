from django.shortcuts import get_object_or_404
from django.views.generic import  list_detail

import plata


def product_list(request):
    shop = plata.shop_instance()

    return list_detail.object_list(request,
        queryset=shop.product_model.objects.active(),
        paginate_by=9,
        )


def product_detail(request, object_id):
    shop = plata.shop_instance()

    return shop.product_detail(request,
        get_object_or_404(shop.product_model.objects.active(), pk=object_id),
        )
