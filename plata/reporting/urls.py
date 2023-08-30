from django.urls import path

from plata.reporting import views


urlpatterns = [
    path("product_xls/", views.product_xls, name="plata_reporting_product_xls"),
    path(
        "invoice_pdf/<int:order_id>/",
        views.invoice_pdf,
        name="plata_reporting_invoice_pdf",
    ),
    path("invoice/<int:order_id>/", views.invoice, name="plata_reporting_invoice"),
    path(
        "packing_slip_pdf/<int:order_id>/",
        views.packing_slip_pdf,
        name="plata_reporting_packing_slip_pdf",
    ),
]
