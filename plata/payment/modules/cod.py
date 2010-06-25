from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import ugettext as _

from plata.payment.modules.base import ProcessorBase
from plata.product.stock.models import StockTransaction
from plata.shop.models import OrderPayment


class PaymentProcessor(ProcessorBase):
    name = _('Cash on delivery')

    def process_order_confirmed(self, request, order):
        if order.is_paid():
            self.order_completed(order)
            return redirect('plata_order_success')

        payment = self.create_pending_payment(order)

        payment.status = OrderPayment.AUTHORIZED
        payment.authorized = datetime.now()
        payment.save()
        order = order.reload()

        self.create_transactions(order, _('sale'),
            type=StockTransaction.SALE, negative=True, payment=payment)
        self.order_completed(order, payment=payment)

        return redirect('plata_order_success')
