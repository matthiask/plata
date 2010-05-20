from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _

from plata.payment.modules.base import ProcessorBase

class PaymentProcessor(ProcessorBase):
    name = _('Cash on delivery')

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url

        return patterns('',
            url(r'payment/cod/$', lambda request: HttpResponse('COD')),
            )

    def process_order_confirmed(self, request, order):
        if order.is_paid():
            return redirect('plata_order_already_paid')

        order.payments.create(
            currency=order.currency,
            amount=order.balance_remaining,
            payment_module=u'%s' % self.name,
            authorized=datetime.now(),
            )

        return redirect('plata_order_success')
