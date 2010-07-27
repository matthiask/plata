from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('plata.reporting.views',
    url(r'^product_xls/$', 'product_xls', name='plata_reporting_product_xls'),
    url(r'^invoice_pdf/(?P<order_id>\d+)/$', 'invoice_pdf', name='plata_reporting_invoice_pdf'),
    url(r'^packing_slip_pdf/(?P<order_id>\d+)/$', 'packing_slip_pdf', name='plata_reporting_packing_slip_pdf'),
)

