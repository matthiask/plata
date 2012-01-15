"""
Exact, transactional stock tracking for Plata
=============================================

Follow these steps to enable this module:

- Ensure your product model has an ``items_in_stock`` field with the following
  definiton::

      items_in_stock = models.IntegerField(default=0)

- Add ``'plata.product.stock'`` to ``INSTALLED_APPS``.
- Set ``PLATA_STOCK_TRACKING = True`` to enable stock tracking in the checkout
  and payment processes.
- Optionally modify your add-to-cart forms on product detail pages to take into
  account ``items_in_stock``.
"""

from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum, Q, signals
from django.utils.translation import ugettext_lazy as _, ugettext

import plata
from plata.shop.models import Order, OrderPayment


class PeriodManager(models.Manager):
    def current(self):
        """
        Return the newest active period
        """

        try:
            return self.filter(start__lte=datetime.now()).order_by('-start')[0]
        except IndexError:
            return self.create(
                name='Automatically created',
                notes='Automatically created because no period existed yet.')


class Period(models.Model):
    """
    A period in which stock changes are tracked

    You might want to create a new period every year and create initial amount
    transactions for every variation. ``StockTransaction.objects.open_new_period``
    does this automatically.
    """

    name = models.CharField(_('name'), max_length=100)
    notes = models.TextField(_('notes'), blank=True)
    start = models.DateTimeField(_('start'), default=datetime.now,
        help_text=_('Period starts at this time. May also be a future date.'))

    class Meta:
        get_latest_by = 'start'
        ordering = ['-start']
        verbose_name = _('period')
        verbose_name_plural = _('periods')

    objects = PeriodManager()

    def __unicode__(self):
        return self.name


class StockTransactionManager(models.Manager):
    def open_new_period(self, name=None):
        """
        Create a new period and create initial transactions for all product
        variations with their current ``items_in_stock`` value
        """

        period = Period.objects.create(name=name or ugettext('New period'))

        for p in plata.product_model()._default_manager.all():
            p.stock_transactions.create(
                period=period,
                type=StockTransaction.INITIAL,
                change=p.items_in_stock,
                notes=ugettext('New period'),
                )

    def _expired(self):
        # 15 minutes expiration time for payment process reservations
        reservation_expiration = datetime.now() - timedelta(minutes=15)

        return Q(type=self.model.PAYMENT_PROCESS_RESERVATION) & Q(created__lt=reservation_expiration)

    def stock(self):
        """
        Return all valid stock transactions (currently all transactions except
        those of type ``PAYMENT_PROCESS_RESERVATION`` older than 15 minutes)
        """

        return self.filter(period=Period.objects.current()).filter(~self._expired())

    def expired(self):
        """
        Return all expired stock transactions (currently only transactions of type
        ``PAYMENT_PROCESS_RESERVATION`` older than 15 minutes)
        """

        return self.filter(period=Period.objects.current()).filter(self._expired())

    def items_in_stock(self, product, update=False, exclude_order=None):
        """
        Determine the items in stock for the given product variation,
        optionally updating the ``items_in_stock`` field in the database.

        If ``exclude_order`` is given, ``update`` is always switched off
        and transactions from the given order aren't taken into account.
        """

        queryset = self.stock().filter(product=product)

        if exclude_order:
            update = False
            queryset = queryset.filter(Q(order__isnull=True) | ~Q(order=exclude_order))

        count = queryset.aggregate(items=Sum('change')).get('items') or 0

        product_model = plata.product_model()

        if isinstance(product, product_model):
            product.items_in_stock = count

        if update:
            product_model._default_manager.filter(id=getattr(product, 'pk', product)).update(
                items_in_stock=count)

        return count

    def bulk_create(self, order, type, negative, **kwargs):
        """
        Create transactions in bulk for every order item

        Set ``negative`` to ``True`` for sales, lendings etc. (anything
        that diminishes the stock you have)
        """

        # Set negative to True for sales, lendings etc.

        factor = negative and -1 or 1

        for item in order.items.all():
            self.model.objects.create(
                product=item.product,
                type=type,
                change=item.quantity * factor,
                order=order,
                **kwargs)


class StockTransaction(models.Model):
    """
    Stores stock transactions transactionally :-)

    Stock transactions basically consist of a product variation reference,
    an amount, a type and a timestamp. The following types are available:

    - ``StockTransaction.INITIAL``: Initial amount, used when filling in the
      stock database
    - ``StockTransaction.CORRECTION``: Use this for any errors
    - ``StockTransaction.PURCHASE``: Product purchase from a supplier
    - ``StockTransaction.SALE``: Sales, f.e. through the webshop
    - ``StockTransaction.RETURNS``: Returned products (from lending or whatever)
    - ``StockTransaction.RESERVATION``: Reservations
    - ``StockTransaction.INCOMING``: Generic warehousing
    - ``StockTransaction.OUTGOING``: Generic warehousing
    - ``StockTransaction.PAYMENT_PROCESS_RESERVATION``: Product reservation
      during payment process

    Most of these types do not have a significance to Plata. The exceptions are:

    - ``INITIAL`` transactions are created by ``open_new_period``
    - ``SALE`` transactions are created when orders are confirmed
    - ``PAYMENT_PROCESS_RESERVATION`` transactions are created by payment modules
      which send the user to a different domain for payment data entry (f.e. PayPal).
      These transactions are also special in that they are only valid for
      15 minutes. After 15 minutes, other customers are able to put the product
      in their cart and proceed to checkout again. This time period is a security
      measure against customers buying products at the same time which cannot
      be delivered afterwards because stock isn't available.
    """

    INITIAL = 10
    CORRECTION = 20
    PURCHASE = 30
    SALE = 40
    RETURNS = 50
    RESERVATION = 60

    # Generic warehousing
    INCOMING = 70
    OUTGOING = 80

    # Semi-internal use
    PAYMENT_PROCESS_RESERVATION = 100 # reservation during payment process

    TYPE_CHOICES = (
        (INITIAL, _('initial amount')),
        (CORRECTION, _('correction')),
        (PURCHASE, _('purchase')),
        (SALE, _('sale')),
        (RETURNS, _('returns')),
        (RESERVATION, _('reservation')),
        (INCOMING, _('incoming')),
        (OUTGOING, _('outgoing')),
        (PAYMENT_PROCESS_RESERVATION, _('payment process reservation')),
        )

    period = models.ForeignKey(Period, default=Period.objects.current,
        related_name='stock_transactions', verbose_name=_('period'))
    created = models.DateTimeField(_('created'), default=datetime.now)
    product = models.ForeignKey(plata.settings.PLATA_SHOP_PRODUCT,
        related_name='stock_transactions', verbose_name=_('product'))
    type = models.PositiveIntegerField(_('type'), choices=TYPE_CHOICES)
    change = models.IntegerField(_('change'),
        help_text=_('Use negative numbers for sales, lendings and other outgoings.'))
    order = models.ForeignKey(Order, blank=True, null=True,
        related_name='stock_transactions', verbose_name=_('order'))
    payment = models.ForeignKey(OrderPayment, blank=True, null=True,
        related_name='stock_transactions', verbose_name=_('order payment'))

    notes = models.TextField(_('notes'), blank=True)

    class Meta:
        ordering = ['-id']
        verbose_name = _('stock transaction')
        verbose_name_plural = _('stock transactions')

    objects = StockTransactionManager()

    def __unicode__(self):
        return u'%s %s of %s' % (
            self.change,
            self.get_type_display(),
            self.product)

    def save(self, *args, **kwargs):
        if not self.period_id:
            self.period = Period.objects.current()

        super(StockTransaction, self).save(*args, **kwargs)


def update_items_in_stock(instance, **kwargs):
    StockTransaction.objects.items_in_stock(instance.product_id, update=True)


def validate_order_stock_available(order):
    """Check whether enough stock is available for all selected products"""
    for item in order.items.all().select_related('product'):
        if item.quantity > StockTransaction.objects.items_in_stock(item.product,
                exclude_order=order):
            raise ValidationError(_('Not enough stock available for %s.') % item.product,
                code='insufficient_stock')


if plata.settings.PLATA_STOCK_TRACKING:
    signals.post_delete.connect(update_items_in_stock, sender=StockTransaction)
    signals.post_save.connect(update_items_in_stock, sender=StockTransaction)

    Order.register_validator(validate_order_stock_available, Order.VALIDATE_CART)
