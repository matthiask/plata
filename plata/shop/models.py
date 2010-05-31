from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Sum
from django.forms.formsets import all_valid
from django.forms.models import modelform_factory, inlineformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _

import plata
from plata.contact.models import BillingShippingAddress, Contact
from plata.discount.models import DiscountBase, Discount
from plata.fields import CurrencyField
from plata.product.models import Product, ProductVariation, TaxClass
from plata.shop import processors
from plata.utils import JSONFieldDescriptor


class Order(BillingShippingAddress):
    CART = 10
    CHECKOUT = 20
    CONFIRMED = 30
    COMPLETED = 40

    STATUS_CHOICES = (
        (CART, _('Is a cart')),
        (CHECKOUT, _('Checkout process started')),
        (CONFIRMED, _('Order has been confirmed')),
        (COMPLETED, _('Order has been completed')),
        )

    created = models.DateTimeField(_('created'), default=datetime.now)
    confirmed = models.DateTimeField(_('confirmed'), blank=True, null=True)
    contact = models.ForeignKey(Contact, verbose_name=_('contact'),
        related_name='orders')
    status = models.PositiveIntegerField(_('status'), choices=STATUS_CHOICES,
        default=CART)

    #order_id = models.CharField(_('order ID'), max_length=20, unique=True)

    currency = CurrencyField()

    items_subtotal = models.DecimalField(_('subtotal'),
        max_digits=18, decimal_places=10, default=Decimal('0.00'))
    items_discount = models.DecimalField(_('items discount'),
        max_digits=18, decimal_places=10, default=Decimal('0.00'))
    items_tax = models.DecimalField(_('items tax'),
        max_digits=18, decimal_places=10, default=Decimal('0.00'))

    shipping_method = models.CharField(_('shipping method'),
        max_length=100, blank=True)
    shipping_cost = models.DecimalField(_('shipping cost'),
        max_digits=18, decimal_places=10, blank=True, null=True)
    shipping_discount = models.DecimalField(_('shipping discount'),
        max_digits=18, decimal_places=10, blank=True, null=True)
    shipping_tax = models.DecimalField(_('shipping tax'),
        max_digits=18, decimal_places=10, default=Decimal('0.00'))

    total = models.DecimalField(_('total'),
        max_digits=18, decimal_places=10, default=Decimal('0.00'))

    paid = models.DecimalField(_('paid'),
        max_digits=18, decimal_places=10, default=Decimal('0.00'),
        help_text=_('This much has been paid already.'))

    notes = models.TextField(_('notes'), blank=True)

    class Meta:
        verbose_name = _('order')
        verbose_name_plural = _('orders')

    def __unicode__(self):
        return u'Order #%d' % self.pk

    def recalculate_total(self, save=True):
        processor = processors.OrderProcessor()
        processor.process(self, list(self.items.all()))

        if save:
            self.save()

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all()).quantize(Decimal('0.00'))

    @property
    def discount(self):
        return (self.subtotal - sum(item.discounted_subtotal for item in self.items.all())).quantize(Decimal('0.00'))

    @property
    def shipping(self):
        if plata.settings.PLATA_PRICE_INCLUDES_TAX:
            return self.shipping_cost - self.shipping_discount + self.shipping_tax
        else:
            raise NotImplementedError

    @property
    def tax(self):
        # TODO shipping tax?
        return self.items_tax.quantize(Decimal('0.00'))

    @property
    def balance_remaining(self):
        return (self.total - self.paid).quantize(Decimal('0.00'))

    def is_paid(self):
        return self.balance_remaining <= 0
    is_paid.boolean = True

    def validate(self):
        """
        A few self-checks. These should never fail under normal circumstances.
        """

        currencies = set(self.items.values_list('currency', flat=True))
        if currencies and (len(currencies) > 1 or self.currency not in currencies):
            raise ValidationError(_('Order contains more than one currency.'),
                code='multiple_currency')

    def modify_item(self, product, relative=None, absolute=None, recalculate=True, **kwargs):
        """
        Update order with the given product

        Return OrderItem instance
        """

        assert (relative is not None and absolute is None) or (absolute is not None and relative is None), 'One of relative or absolute must be provided.'

        if self.status >= self.CONFIRMED:
            raise ValidationError(_('Cannot modify order once it has been confirmed.'),
                code='order_sealed')

        if isinstance(product, ProductVariation):
            product, variation = product.product, product
        else:
            product, variation = product, product.variations.get(**kwargs)

        # TODO handle missing price instead of failing up the stack
        price = product.get_price(currency=self.currency)

        try:
            item = self.items.get(variation=variation)
        except self.items.model.DoesNotExist:
            item = self.items.model(
                order=self,
                variation=variation,
                quantity=0,
                currency=self.currency,
                )

        item._unit_price = price.unit_price_excl_tax
        item._unit_tax = price.unit_tax
        item.tax_class = price.tax_class
        item.is_sale = price.is_sale

        if relative is not None:
            item.quantity += relative
        else:
            item.quantity = absolute

        if item.quantity > 0:
            item.save()
        else:
            # TODO: Should zero and negative values be handled the same way?
            item.delete()
            item.pk = None

        if recalculate:
            self.recalculate_total()

            # Reload item instance from DB to preserve field values
            # changed in recalculate_total
            if item.pk:
                item = self.items.get(pk=item.pk)

        try:
            self.validate()
        except ValidationError:
            if item.pk:
                item.delete()
            raise

        return item

    def add_discount(self, discount, recalculate=True):
        discount.validate(self)

        instance, created = self.applied_discounts.get_or_create(code=discount.code,
            defaults={
                'type': discount.type,
                'name': discount.name,
                'value': discount.value,
                'config_json': discount.config_json,
            })

        if recalculate:
            self.recalculate_total()

        return instance

    @property
    def discount_remaining(self):
        discounts_excl = sum((d.value for d in self.applied_discounts.filter(
            type=DiscountBase.AMOUNT_EXCL_TAX)), 0)
        discounts_incl = sum((d.value for d in self.applied_discounts.filter(
            type=DiscountBase.AMOUNT_INCL_TAX)), 0)

        # TODO remove hardcoded tax rate
        remaining = (discounts_excl * Decimal('1.076') + discounts_incl) - self.discount

        if remaining > 0:
            return remaining
        return Decimal('0.00')

    def update_status(self, status, notes):
        if status >= Order.CHECKOUT:
            if not self.items.count():
                raise ValidationError(_('Cannot proceed to checkout without order items.'),
                    code='order_empty')

        instance = OrderStatus(
            order=self,
            status=status,
            notes=notes)
        instance.save()


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items')
    variation = models.ForeignKey(ProductVariation, verbose_name=_('product variation'))

    quantity = models.IntegerField(_('quantity'))

    currency = CurrencyField()
    _unit_price = models.DecimalField(_('unit price'),
        max_digits=18, decimal_places=10,
        help_text=_('Unit price excl. tax'))
    _unit_tax = models.DecimalField(_('unit tax'),
        max_digits=18, decimal_places=10)
    tax_class = models.ForeignKey(TaxClass, verbose_name=_('tax class'))
    is_sale = models.BooleanField(_('is sale'))

    _line_item_price = models.DecimalField(_('line item price'),
        max_digits=18, decimal_places=10, default=0,
        help_text=_('Line item price excl. tax'))
    _line_item_discount = models.DecimalField(_('discount'),
        max_digits=18, decimal_places=10,
        blank=True, null=True,
        help_text=_('Discount excl. tax'))

    _line_item_tax = models.DecimalField(_('line item tax'),
        max_digits=18, decimal_places=10, default=0)

    class Meta:
        ordering = ('variation',)
        unique_together = (('order', 'variation'),)
        verbose_name = _('order item')
        verbose_name_plural = _('order items')

    def __unicode__(self):
        return u'%s of %s' % (self.quantity, self.variation)

    @property
    def unit_price(self):
        if plata.settings.PLATA_PRICE_INCLUDES_TAX:
            return self._unit_price + self._unit_tax
        return self._unit_price

    @property
    def line_item_discount_excl_tax(self):
        return self._line_item_discount or 0

    @property
    def line_item_discount_incl_tax(self):
        return self.line_item_discount_excl_tax * (1+self.tax_class.rate/100)

    @property
    def line_item_discount(self):
        if plata.settings.PLATA_PRICE_INCLUDES_TAX:
            return self.line_item_discount_incl_tax
        else:
            return self.line_item_discount_excl_tax

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    @property
    def discounted_subtotal_excl_tax(self):
        return self._line_item_price - (self._line_item_discount or 0)

    @property
    def discounted_subtotal_incl_tax(self):
        return self.discounted_subtotal_excl_tax + self._line_item_tax

    @property
    def discounted_subtotal(self):
        if plata.settings.PLATA_PRICE_INCLUDES_TAX:
            return self.discounted_subtotal_incl_tax
        else:
            return self.discounted_subtotal_excl_tax


class OrderStatus(models.Model):
    order = models.ForeignKey(Order, related_name='statuses')
    created = models.DateTimeField(_('created'), default=datetime.now)
    status = models.PositiveIntegerField(_('status'), max_length=20, choices=Order.STATUS_CHOICES)
    notes = models.TextField(_('notes'), blank=True)

    class Meta:
        get_latest_by = 'created'
        ordering = ('created',)
        verbose_name = _('order status')
        verbose_name_plural = _('order statuses')

    def __unicode__(self):
        return u'Status %s for %s' % (self.get_status_display(), self.order)

    def save(self, *args, **kwargs):
        super(OrderStatus, self).save(*args, **kwargs)
        self.order.status = self.status
        if self.status >= Order.CONFIRMED and not self.order.confirmed:
            self.order.confirmed = datetime.now()
        self.order.save()


class OrderPayment(models.Model):
    order = models.ForeignKey(Order, verbose_name=_('order'), related_name='payments')
    timestamp = models.DateTimeField(_('timestamp'), default=datetime.now)

    currency = CurrencyField()
    amount = models.DecimalField(_('amount'), max_digits=10, decimal_places=2)
    payment_module = models.CharField(_('payment module'), max_length=50, blank=True,
        help_text=_('For example \'Cash on delivery\', \'PayPal\', ...'))
    payment_method = models.CharField(_('payment method'), max_length=50, blank=True,
        help_text=_('For example \'MasterCard\', \'VISA\' or some other card.'))
    transaction_id = models.CharField(_('transaction ID'), max_length=50, blank=True,
        help_text=_('Unique ID identifying this payment in the foreign system.'))

    authorized = models.DateTimeField(_('authorized'), blank=True, null=True,
        help_text=_('Point in time when payment has been authorized.'))

    notes = models.TextField(_('notes'), blank=True)

    data_json = models.TextField(_('data'), blank=True,
        help_text=_('JSON-encoded additional data about the order payment.'))
    data = JSONFieldDescriptor('data_json')

    class Meta:
        ordering = ('-timestamp',)
        verbose_name = _('order payment')
        verbose_name_plural = _('order payments')

    def __unicode__(self):
        if self.authorized:
            return u'Authorized payment of %s %.2f for %s' % (
                self.currency,
                self.amount,
                self.order,
                )
        return u'Not authorized payment of %s %.2f for %s' % (
            self.currency,
            self.amount,
            self.order,
            )

    def _recalculate_paid(self):
        paid = OrderPayment.objects.filter(
            order=self.order_id,
            authorized__isnull=False,
            ).aggregate(total=Sum('amount'))['total'] or 0

        Order.objects.filter(id=self.order_id).update(paid=paid)

    def save(self, *args, **kwargs):
        # TODO raise error if currencies to not match
        super(OrderPayment, self).save(*args, **kwargs)
        self._recalculate_paid()

    def delete(self, *args, **kwargs):
        super(OrderPayment, self).delete(*args, **kwargs)
        self._recalculate_paid()


class AppliedDiscount(DiscountBase):
    order = models.ForeignKey(Order, related_name='applied_discounts',
        verbose_name=_('order'))
    code = models.CharField(_('code'), max_length=30) # We could make this a ForeignKey
                                                      # to Discount.code, but we do not
                                                      # want deletions to cascade to this
                                                      # table.

    class Meta:
        verbose_name = _('applied discount')
        verbose_name_plural = _('applied discounts')
