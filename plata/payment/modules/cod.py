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

        StockTransaction.objects.bulk_create(order,
            type=StockTransaction.SALE,
            notes=_('%(type)s transaction. %(order)s processed by %(payment_module)s') % {
                'type': _('sale'),
                'order': order,
                'payment_module': self.name,
                },
            negative=True,
            payment=payment)

        return redirect('plata_order_success')
