from django.http import HttpResponse


class PaymentProcessor(object):
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
