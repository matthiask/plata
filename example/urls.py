import os

from django.conf.urls.defaults import *
from django.contrib import admin
from django.shortcuts import redirect

from plata.product.feincms.models import CMSProduct
from plata.shop.views import Shop
from plata.shop.models import Product, Contact, Order, Discount


admin.autodiscover()

shop = Shop(CMSProduct, Contact, Order, Discount)


urlpatterns = patterns('',
    url(r'', include(shop.urls)),
    url(r'^admin/', include(admin.site.urls)),

    url(r'^$', lambda request: redirect('plata_product_list')),
    url(r'^products/$', 'example.views.product_list',
        name='plata_product_list'),
    url(r'^products/(?P<object_id>\d+)/$', 'example.views.product_detail',
        name='plata_product_detail'),

    (r'^media/sys/feincms/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': os.path.join(os.path.dirname(os.path.dirname(__file__)), 'feincms/media/feincms/')}),

    (r'^media/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': os.path.join(os.path.dirname(__file__), 'media/')}),
)
