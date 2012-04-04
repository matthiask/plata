import logging

from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _

import plata
from plata.product.stock.models import StockTransaction
from plata.shop import signals


logger = logging.getLogger('plata.payment')


class ProcessorBase(object):
    """Payment processor base class"""

    #: Safe key for this payment module (shouldn't contain special chars, spaces etc.)
    key = 'unnamed'

    #: Human-readable name for this payment module. You may even use i18n here.
    default_name = 'unnamed'

    def __init__(self, shop):
        self.shop = shop

    @property
    def name(self):
        """
        Return name of this payment module suitable for human consumption

        Defaults to ``default_name`` but can be overridden by placing an entry
        in ``PLATA_PAYMENT_MODULE_NAMES``. Example::

            PLATA_PAYMENT_MODULE_NAMES = {
                'paypal': _('Paypal and credit cards'),
                }
        """
        return plata.settings.PLATA_PAYMENT_MODULE_NAMES.get(
            self.key,
            self.default_name)

    @property
    def urls(self):
        """
        Return URLconf definitions used by this payment processor

        This is especially useful for processors offering server-to-server
        communication such as Paypal's IPN (Instant Payment Notification) where
        Paypal communicates payment success immediately and directly, without
        involving the client.

        Define your own URLs in ``get_urls``.
        """
        return self.get_urls()

    def get_urls(self):
        """
        Define URLs for this payment processor

        Note that these URLs are added directly to the shop views URLconf
        without prefixes. It is your responsability to namespace these URLs
        so they don't clash with shop views and other payment processors.
        """
        from django.conf.urls.defaults import patterns
        return patterns('')

    def enabled_for_request(self, request):
        """
        Decides whether or not this payment modules is available for a given request.

        Defaults to ``True``. If you need to disable payment modules for certain
        visitors or group of visitors, that is the method you are searching for.
        """
        return True

    def process_order_confirmed(self, request, order):
        """
        This is the initial entry point of payment modules and is called when
        the user has selected a payment module and accepted the terms and
        conditions of the shop.

        Must return a response which is presented to the user, i.e. a form with
        hidden values forwarding the user to the PSP or a redirect to the success
        page if no further processing is needed.
        """
        raise NotImplementedError

    def clear_pending_payments(self, order):
        """
        Clear pending payments
        """
        logger.info('Clearing pending payments on %s' % order)

        if plata.settings.PLATA_STOCK_TRACKING:
            for transaction in order.stock_transactions.filter(
                    type=StockTransaction.PAYMENT_PROCESS_RESERVATION):
                transaction.delete()

        order.payments.pending().delete()

    def create_pending_payment(self, order):
        """
        Create a pending payment
        """
        self.clear_pending_payments(order)
        logger.info('Creating pending payment on %s' % order)
        return order.payments.create(
            currency=order.currency,
            amount=order.balance_remaining,
            payment_module_key=self.key,
            payment_module=u'%s' % self.name,
            )

    def create_transactions(self, order, stage, **kwargs):
        """
        Create transactions for all order items. The real work is offloaded
        to ``StockTransaction.objects.bulk_create``.
        """

        if not plata.settings.PLATA_STOCK_TRACKING:
            return

        StockTransaction.objects.bulk_create(order,
            notes=_('%(stage)s: %(order)s processed by %(payment_module)s') % {
                'stage': stage,
                'order': order,
                'payment_module': self.name,
                },
            **kwargs)

    def order_paid(self, order, payment=None):
        """
        Call this when the order has been fully paid for

        This method does the following:

        - Sets order status to ``PAID``.
        - Calculates the remaining discount amount (if any) and calls the
          ``order_paid`` signal.
        - Clears pending payments which aren't interesting anymore anyway.
        """

        if order.status < order.PAID:
            logger.info('Order %s has been completely paid for using %s' % (
                order, self.name))
            order.update_status(order.PAID, 'Order has been paid')

            signal_kwargs = dict(sender=self, order=order, payment=payment)

            if order.discount_remaining:
                logger.info('Creating discount for remaining amount %s on order %s' % (
                    order.discount_remaining, order))
                discount_model = self.shop.discount_model
                try:
                    discount = order.applied_discounts.filter(
                        type__in=(discount_model.AMOUNT_VOUCHER_EXCL_TAX, discount_model.AMOUNT_VOUCHER_INCL_TAX),
                        ).order_by('type')[0]
                except IndexError:
                    # XXX: Remaining discount will be applicable to ALL products,
                    # not sure if this behavior is correct...
                    discount = None

                signal_kwargs['remaining_discount'] = discount_model.objects.create(
                    name='Remaining discount amount for order #%s' % order.pk,
                    type=self.shop.discount_model.AMOUNT_VOUCHER_EXCL_TAX,
                    value=order.discount_remaining,
                    currency=order.currency,
                    config=getattr(discount, 'config', '{"all": {}}'),
                    allowed_uses=1,
                    )

            signals.order_paid.send(**signal_kwargs)
        self.clear_pending_payments(order)

    def already_paid(self, order):
        """
        Handles the case where a payment module is selected but the order
        is already completely paid for (f.e. because an amount discount has been
        used which covers the order).

        Does nothing if the order **status** is ``PAID`` already.
        """
        if order.status < order.PAID:
            logger.info('Order %s is already completely paid' % order)

            if plata.settings.PLATA_STOCK_TRACKING:
                self.create_transactions(order, _('sale'),
                    type=StockTransaction.SALE, negative=True)

            self.order_paid(order)

        return redirect('plata_order_success')
