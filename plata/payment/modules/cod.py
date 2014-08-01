"""
Payment module for cash on delivery handling

Automatically completes every order passed.
"""

from __future__ import absolute_import, unicode_literals

import logging

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

import plata
from plata.payment.modules.base import ProcessorBase
from plata.shop.models import OrderPayment


logger = logging.getLogger('plata.payment.cod')


class PaymentProcessor(ProcessorBase):
    key = 'cod'
    default_name = _('Cash on delivery')

    def process_order_confirmed(self, request, order):
        if not order.balance_remaining:
            return self.already_paid(order)

        logger.info('Processing order %s using COD' % order)

        payment = self.create_pending_payment(order)

        payment.status = OrderPayment.AUTHORIZED
        payment.authorized = timezone.now()
        payment.save()
        order = order.reload()

        if plata.settings.PLATA_STOCK_TRACKING:
            StockTransaction = plata.stock_model()
            self.create_transactions(
                order, _('sale'),
                type=StockTransaction.SALE, negative=True, payment=payment)
        self.order_paid(order, payment=payment, request=request)

        return self.shop.redirect('plata_order_success')
