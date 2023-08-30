import os

from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.shortcuts import redirect
from django.urls import include, path, re_path
from django.views.static import serve

from custom.views import product_detail, product_list, shop


admin.autodiscover()


urlpatterns = [
    path("", include(shop.urls)),
    path("admin/", include(admin.site.urls)),
    path("", lambda request: redirect("plata_product_list"), name="plata_home"),
    path("dashboard/", lambda request: redirect("/admin/"), name="dashboard"),
    path("products/", product_list, name="plata_product_list"),
    path("products/<int:object_id>/", product_detail, name="plata_product_detail"),
    path("reporting/", include("plata.reporting.urls")),
    re_path(
        r"^media/(?P<path>.*)$",
        serve,
        {"document_root": os.path.join(os.path.dirname(__file__), "media/")},
    ),
]

urlpatterns += staticfiles_urlpatterns()
