from datetime import datetime, timedelta

from django.db import models
from django.db.models import Sum, Q, signals
from django.utils.translation import ugettext_lazy as _, ugettext

from plata.product.models import ProductVariation
from plata.shop.models import Order, OrderPayment


class PeriodManager(models.Manager):
    def current(self):
        try:
            return self.filter(start__lte=datetime.now()).order_by('-start')[0]
        except IndexError:
            return None


class Period(models.Model):
    name = models.CharField(_('name'), max_length=100)
    notes = models.TextField(_('notes'), blank=True)
    start = models.DateTimeField(_('start'), default=datetime.now)

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
        period = Period.objects.create(name=name or ugettext('New period'))

        for p in ProductVariation.objects.all():
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
        return self.filter(period=Period.objects.current()).filter(~self._expired())

    def expired(self):
        return self.filter(period=Period.objects.current()).filter(self._expired())

    def items_in_stock(self, product, update=False, query=None):
        queryset = self.stock().filter(product=product)
        if query:
            queryset.filter(query)

        count = queryset.aggregate(items=Sum('change')).get('items') or 0

        if update:
            ProductVariation.objects.filter(id=getattr(product, 'pk', product)).update(
                items_in_stock=count)
        return count

    def bulk_create(self, order, type, negative=False, **kwargs):
        # Set negative to True for sales, lendings etc.

        factor = negative and -1 or 1

        for item in order.items.all():
            self.model.objects.create(
                product=item.variation,
                type=type,
                change=item.quantity * factor,
                order=order,
                **kwargs)


class StockTransaction(models.Model):
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
    product = models.ForeignKey(ProductVariation, related_name='stock_transactions',
        verbose_name=_('product variation'))
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
            self.period = Period.objects.create(name='Automatically created',
                notes='Automatically created because no period existed yet.')

        super(StockTransaction, self).save(*args, **kwargs)


def update_items_in_stock(instance, **kwargs):
    StockTransaction.objects.items_in_stock(instance.product_id, update=True)
signals.post_delete.connect(update_items_in_stock, sender=StockTransaction)
signals.post_save.connect(update_items_in_stock, sender=StockTransaction)
