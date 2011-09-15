"""
Payment module for cash on delivery handling

Automatically completes every order passed.
"""

from datetime import datetime
import logging

from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _

from plata.payment.modules.base import ProcessorBase
from plata.product.stock.models import StockTransaction
from plata.shop.models import OrderPayment


logger = logging.getLogger('plata.payment.cod')


class PaymentProcessor(ProcessorBase):
    key = 'cod'
    default_name = _('Cash on delivery')

    def process_order_confirmed(self, request, order):
        if order.is_paid():
            return self.already_paid(order)

        logger.info('Processing order %s using COD' % order)

        payment = self.create_pending_payment(order)

        payment.status = OrderPayment.AUTHORIZED
        payment.authorized = datetime.now()
        payment.save()
        order = order.reload()

        self.create_transactions(order, _('sale'),
            type=StockTransaction.SALE, negative=True, payment=payment)
        self.order_completed(order, payment=payment)

        return redirect('plata_order_success')
