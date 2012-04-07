from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.shortcuts import redirect

from plata.contact.models import Contact
from plata.discount.models import Discount
from plata.shop.models import Order
from plata.shop.views import Shop


admin.autodiscover()

shop = Shop(
    contact_model=Contact,
    order_model=Order,
    discount_model=Discount,
    )


urlpatterns = patterns('',
    url(r'^$', lambda request: redirect('plata_product_list')),
    url(r'', include(shop.urls)),
    url(r'^products/$', 'testapp.views.product_list',
        name='plata_product_list'),
    url(r'^products/(\d+)/$', 'testapp.views.product_detail',
        name='plata_product_detail'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^reporting/', include('plata.reporting.urls')),
)
