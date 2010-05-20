from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _


class PaymentProcessor(object):
    name = _('Cash on delivery')

    def __init__(self, shop):
        self.shop = shop

    @property
    def urls(self):
        return self.get_urls()

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url

        return patterns('',
            url(r'payment/cod/$', lambda request: HttpResponse('COD')),
            )
