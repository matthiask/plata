from datetime import datetime
import logging

from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _

from plata.product.stock.models import StockTransaction
from plata.shop import signals


logger = logging.getLogger('plata.payment')


class ProcessorBase(object):
    name = 'unnamed'

    def __init__(self, shop):
        self.shop = shop

    @property
    def urls(self):
        return self.get_urls()

    def get_urls(self):
        # Please note that these patterns are added with global scope;
        # You should define URLs which do not clash with other parts
        # of the site yourself.
        from django.conf.urls.defaults import patterns, url
        return patterns('')

    def process_order_confirmed(self, request, order):
        raise NotImplementedError

    def clear_pending_payments(self, order):
        logger.info('Clearing pending payments on %s' % order)
        order.payments.pending().delete()
        order.stock_transactions.filter(type=StockTransaction.PAYMENT_PROCESS_RESERVATION).delete()

    def create_pending_payment(self, order):
        self.clear_pending_payments(order)
        logger.info('Creating pending payment on %s' % order)
        return order.payments.create(
            currency=order.currency,
            amount=order.balance_remaining,
            payment_module=u'%s' % self.name,
            )

    def create_transactions(self, order, stage, **kwargs):
        StockTransaction.objects.bulk_create(order,
            notes=_('%(stage)s: %(order)s processed by %(payment_module)s') % {
                'stage': stage,
                'order': order,
                'payment_module': self.name,
                },
            **kwargs)

    def order_completed(self, order, payment=None):
        if order.status < order.PAID:
            logger.info('Order %s has been completely paid for using %s' % (
                order, self.name))
            order.update_status(order.PAID, 'Order has been fully paid')

            signal_kwargs = dict(sender=self, order=order, payment=payment)

            if order.discount_remaining:
                logger.info('Creating discount for remaining amount %s on order %s' % (
                    order.discount_remaining, order))
                discount_model = self.shop.discount_model
                try:
                    discount = order.applied_discounts.filter(
                        type__in=(discount_model.AMOUNT_EXCL_TAX, discount_model.AMOUNT_INCL_TAX),
                        ).order_by('type')[0]
                except IndexError:
                    discount = None

                signal_kwargs['remaining_discount'] = discount_model.objects.create(
                    name='Remaining discount amount for order #%s' % order.pk,
                    type=self.shop.discount_model.AMOUNT_EXCL_TAX,
                    value=order.discount_remaining,
                    config_json=getattr(discount, 'config_json', '{"all": {}}'),
                    allowed_uses=1,
                    )

            signals.order_completed.send(**signal_kwargs)
        self.clear_pending_payments(order)
