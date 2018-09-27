import os
from django.conf.urls import include, url
from django.contrib import admin
from django.shortcuts import redirect
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.static import serve
from oneprice.views import shop, product_list, product_detail


admin.autodiscover()


urlpatterns = [
    url(r"", include(shop.urls)),
    url(r"^admin/", include(admin.site.urls)),
    url(r"^$", lambda request: redirect("plata_product_list"), name="plata_home"),
    url(r"^dashboard/$", lambda request: redirect("/admin/"), name="dashboard"),
    url(r"^products/$", product_list, name="plata_product_list"),
    url(r"^products/(?P<object_id>\d+)/$", product_detail, name="plata_product_detail"),
    url(
        r"^media/(?P<path>.*)$",
        serve,
        {"document_root": os.path.join(os.path.dirname(__file__), "media/")},
    ),
]

urlpatterns += staticfiles_urlpatterns()
