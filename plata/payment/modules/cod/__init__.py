from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import redirect
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

    def process_order_confirmed(self, request, order):
        order.payments.create(
            currency=order.currency,
            amount=order.total,
            payment_method=u'%s' % self.name,
            authorized=datetime.now(),
            )

        return redirect('plata_order_success')
