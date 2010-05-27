from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import ugettext as _

from plata.payment.modules.base import ProcessorBase
from plata.product.stock.models import StockTransaction


class PaymentProcessor(ProcessorBase):
    name = _('Cash on delivery')

    def process_order_confirmed(self, request, order):
        if order.is_paid():
            return redirect('plata_order_already_paid')

        payment = order.payments.create(
            currency=order.currency,
            amount=order.balance_remaining,
            payment_module=u'%s' % self.name,
            authorized=datetime.now(),
            )

        self.create_transactions(order, _('sale'),
            type=StockTransaction.SALE, negative=True, payment=payment)

        return redirect('plata_order_success')
