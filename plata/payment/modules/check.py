"""
Payment module for check/transfert

Author: jpbraun@mandriva.com
"""

import logging
from decimal import Decimal
from uuid import uuid4

from django.utils.translation import ugettext_lazy as _
from django.http import Http404, HttpResponse
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site

import plata
from plata.payment.modules.base import ProcessorBase
from plata.shop.models import Order, OrderPayment


logger = logging.getLogger('plata.payment.check')


class PaymentProcessor(ProcessorBase):
    key = 'check'
    default_name = _('Check/Transfert')

    def get_urls(self):
        from django.conf.urls import patterns, url

        return patterns(
            '',
            url(r'^payment/check/confirm/(?P<uuid>[^/]+)/$', self.confirm,
                name='plata_payment_check_confirm'),
        )

    def process_order_confirmed(self, request, order):
        if not order.balance_remaining:
            return self.already_paid(order)

        logger.info('Processing order %s using check' % order)

        payment = self.create_pending_payment(order)

        order.notes = str(uuid4())
        order.save()

        if plata.settings.PLATA_STOCK_TRACKING:
            StockTransaction = plata.stock_model()
            self.create_transactions(order, _('sale'),
                                     type=StockTransaction.SALE,
                                     negative=True,
                                     payment=payment)
        current_site = Site.objects.get_current()
        confirm_link = "https://%s%s" % (current_site.domain, reverse('plata_payment_check_confirm', kwargs={'uuid': order.notes}))
        message = """The order %s has been confirmed for check or bank transfert.

Items: %s

Amount due: %s %s

Click on this link when the payment is received: %s
""" % (order, "\n   -".join([unicode(item) for item in order.items.all()]), order.balance_remaining, order.currency, confirm_link)

        send_mail('New check/bank order (%s)' % order,
                  message,
                  settings.SERVER_EMAIL,
                  settings.PLATA_PAYMENT_CHECK_NOTIFICATIONS)

        return self.shop.render(request, 'payment/check_informations.html',
                                {'order': order,
                                 'payment': payment,
                                 'HTTP_HOST': request.META.get('HTTP_HOST')})

    def confirm(self, request, uuid):

        try:
            order = Order.objects.get(notes=uuid)
        except Order.DoesNotExists:
            raise Http404

        payment = list(order.payments.all()[:1])[0]
        payment.authorized = timezone.now()
        payment.status = OrderPayment.AUTHORIZED
        payment.amount = Decimal(order.balance_remaining)
        payment.currency = order.currency
        payment.payment_method = self.name
        payment.save()
        order.paid = order.total
        order.save()

        self.order_paid(order, payment=payment)
        return HttpResponse("OK")
