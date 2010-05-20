from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt


csrf_exempt_m = method_decorator(csrf_exempt)


class PaymentProcessor(object):
    name = _('Postfinance')

    def __init__(self, shop):
        self.shop = shop

    @property
    def urls(self):
        return self.get_urls()

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url

        return patterns('',
            url(r'^payment/postfinance/$', lambda request: HttpResponse('COD')),
            url(r'^payment/postfinance/ipn/$', lambda request: HttpResponse('IPN')),
            )

    def process_order_confirmed(self, request, order):
        order.payments.create(
            currency=order.currency,
            amount=order.total,
            payment_method=u'%s' % self.name,
            authorized=datetime.now(),
            )

        return redirect('plata_order_success')

    @csrf_exempt_m
    def ipn(self, request):
        raise NotImplementedError
