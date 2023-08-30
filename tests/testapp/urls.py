from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path, re_path

from plata.contact.models import Contact
from plata.discount.models import Discount
from plata.shop.models import Order
from plata.shop.views import Shop
from testapp import views


admin.autodiscover()

shop = Shop(contact_model=Contact, order_model=Order, discount_model=Discount)


urlpatterns = [
    path("", lambda request: redirect("plata_product_list"), name="plata_home"),
    path("", include(shop.urls)),
    path("products/", views.product_list, name="plata_product_list"),
    re_path(r"^products/(\d+)/$", views.product_detail, name="plata_product_detail"),
    re_path(r"^admin/", admin.site.urls),
    path("reporting/", include("plata.reporting.urls")),
]
