from django.conf.urls.defaults import *
from django.contrib import admin

from plata.shop.views import Shop
from plata.shop.models import Product, Contact, Order


admin.autodiscover()

shop = Shop(Product, Contact, Order)

urlpatterns = patterns('',
    url(r'^plata/', include(shop.urls)),
    url(r'^admin/', include(admin.site.urls)),
)
