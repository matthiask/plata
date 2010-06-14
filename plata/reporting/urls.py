from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('plata.reporting.views',
    url(r'order_pdf/(?P<order_id>\d+)/$', 'order_pdf', name='plata_reporting_order_pdf'),
)
