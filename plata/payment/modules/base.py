from datetime import datetime
import logging

from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _

import plata
from plata.product.stock.models import StockTransaction
from plata.shop import signals


logger = logging.getLogger('plata.payment')


class ProcessorBase(object):
    """Payment processor base class"""

    #: Safe key for this payment module (shouldn't contain special chars, spaces etc.)
    ident = 'unnamed'

    #: Human-readable name for this payment module. You may even use i18n here.
    default_name = 'unnamed'

    def __init__(self, shop):
        self.shop = shop

    @property
    def name(self):
        return plata.settings.PLATA_PAYMENT_MODULE_NAMES.get(
            self.ident,
            self.default_name)

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
        """
        Process order confirmation

        Must return a response which is presented to the user (e.g. a
        form with hidden values redirecting to the PSP)
        """

        raise NotImplementedError

    def clear_pending_payments(self, order):
        """
        Clear pending payments
        """

        logger.info('Clearing pending payments on %s' % order)
        order.payments.pending().delete()
        order.stock_transactions.filter(type=StockTransaction.PAYMENT_PROCESS_RESERVATION).delete()

    def create_pending_payment(self, order):
        """
        Create a pending payment
        """

        self.clear_pending_payments(order)
        logger.info('Creating pending payment on %s' % order)
        return order.payments.create(
            currency=order.currency,
            amount=order.balance_remaining,
            payment_module=u'%s' % self.name,
            )

    def create_transactions(self, order, stage, **kwargs):
        """
        Create transactions for all order items. The real work is offloaded
        to ``StockTransaction.objects.bulk_create``.
        """

        StockTransaction.objects.bulk_create(order,
            notes=_('%(stage)s: %(order)s processed by %(payment_module)s') % {
                'stage': stage,
                'order': order,
                'payment_module': self.name,
                },
            **kwargs)

    def order_completed(self, order, payment=None):
        """
        Call this when payment has been confirmed
        """

        if order.status < order.COMPLETED:
            logger.info('Order %s has been completely paid for using %s' % (
                order, self.name))
            order.update_status(order.COMPLETED, 'Order has been completed')

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
                    currency=order.currency,
                    config_json=getattr(discount, 'config_json', '{"all": {}}'),
                    allowed_uses=1,
                    )

            signals.order_completed.send(**signal_kwargs)
        self.clear_pending_payments(order)
