from __future__ import unicode_literals

from django.conf.urls import url

from plata.reporting import views


urlpatterns = [
    url(r'^product_xls/$',
        views.product_xls,
        name='plata_reporting_product_xls'),
    url(r'^invoice_pdf/(?P<order_id>\d+)/$',
        views.invoice_pdf,
        name='plata_reporting_invoice_pdf'),
    url(r'^invoice/(?P<order_id>\d+)/$',
        views.invoice,
        name='plata_reporting_invoice'),
    url(r'^packing_slip_pdf/(?P<order_id>\d+)/$',
        views.packing_slip_pdf,
        name='plata_reporting_packing_slip_pdf'),
]
