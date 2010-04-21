from django.conf.urls.defaults import *
from django.contrib import admin

from plata.shop.views import Shop
from plata.shop.models import Product, Contact, Order


admin.autodiscover()


urlpatterns = patterns('',
    url(r'^plata/', include(Shop(Product, Contact, Order).urls)),
    url(r'^admin/', include(admin.site.urls)),
)
