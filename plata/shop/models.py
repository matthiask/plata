from datetime import datetime
from decimal import Decimal
import logging

from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import F, ObjectDoesNotExist, Sum
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


logger = logging.getLogger('plata.shop.order')

class Order(BillingShippingAddress):
    """The main order model. Used for carts and orders alike."""
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
    contact = models.ForeignKey(Contact, blank=True, null=True,
        verbose_name=_('contact'), related_name='orders')
    status = models.PositiveIntegerField(_('status'), choices=STATUS_CHOICES,
        default=CART)

    #order_id = models.CharField(_('order ID'), max_length=20, unique=True)
    email = models.EmailField(_('e-mail address'))

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

    data_json = models.TextField(_('data'), blank=True,
        help_text=_('JSON-encoded additional data about the order payment.'))
    data = JSONFieldDescriptor('data_json')

    class Meta:
        verbose_name = _('order')
        verbose_name_plural = _('orders')

    def __unicode__(self):
        return u'Order #%d' % self.pk

    def recalculate_total(self, save=True):
        """
        Recalculate totals, discounts, taxes.
        """

        items = self.items.all()

        processor = processors.OrderProcessor()
        processor.process(self, items)

        if save:
            self.save()
            [item.save() for item in items]

    @property
    def subtotal(self):
        return sum((item.subtotal for item in self.items.all()), Decimal('0.00')).quantize(Decimal('0.00'))

    @property
    def discount(self):
        return (sum((item.subtotal for item in self.items.all()), Decimal('0.00')) -
            sum((item.discounted_subtotal for item in self.items.all()), Decimal('0.00'))).quantize(Decimal('0.00'))

    @property
    def shipping(self):
        if plata.settings.PLATA_PRICE_INCLUDES_TAX:
            if self.shipping_cost is None:
                return None

            return self.shipping_cost - self.shipping_discount + self.shipping_tax
        else:
            logger.error('Shipping calculation with PLATA_PRICE_INCLUDES_TAX=False is not implemented yet')
            raise NotImplementedError

    @property
    def tax(self):
        return (self.items_tax + self.shipping_tax).quantize(Decimal('0.00'))

    @property
    def balance_remaining(self):
        return (self.total - self.paid).quantize(Decimal('0.00'))

    def is_paid(self):
        return self.balance_remaining <= 0
    is_paid.boolean = True

    def is_confirmed(self):
        return self.status >= self.CONFIRMED
    is_confirmed.boolean = True

    def is_completed(self):
        return self.status >= self.COMPLETED
    is_completed.boolean = True


    VALIDATE_BASE = 10
    VALIDATE_CART = 20
    VALIDATE_CHECKOUT = 30
    VALIDATE_ALL = 100

    VALIDATORS = {}

    @classmethod
    def register_validator(cls, validator, group):
        """
        Register another order validator in a validation group

        A validator is a callable accepting an order (and only an order).

        There are several types of order validators:

        - Base validators are always called
        - Cart validators: Need to validate for a valid cart
        - Checkout validators: Need to validate in the checkout process
        """

        cls.VALIDATORS.setdefault(group, []).append(validator)

    def validate(self, group):
        """
        Validate this order

        The argument determines which order validators are called:

        - ``Order.VALIDATE_BASE``
        - ``Order.VALIDATE_CART``
        - ``Order.VALIDATE_CHECKOUT``
        - ``Order.VALIDATE_ALL``
        """

        for g in sorted(g for g in self.VALIDATORS.keys() if g<=group):
            for validator in self.VALIDATORS[g]:
                validator(self)

    def modify_item(self, product, relative=None, absolute=None, recalculate=True, **kwargs):
        """
        Update order with the given product

        - ``relative`` or ``absolute``: Add/subtract or define order item amount exactly
        - ``recalculate``: Recalculate order after cart modification (defaults to ``True``)

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

        try:
            price = product.get_price(currency=self.currency)
        except ObjectDoesNotExist:
            logger.error('No price could be found for %s with currency %s' % (
                product, self.currency))
            raise

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
        item.tax_rate = price.tax_class.rate
        item.tax_class = price.tax_class
        item.is_sale = price.is_sale

        if relative is not None:
            item.quantity += relative
        else:
            item.quantity = absolute

        if item.quantity > 0:
            item.save()
        else:
            if item.pk:
                item.delete()
                item.pk = None

        if recalculate:
            self.recalculate_total()

            # Reload item instance from DB to preserve field values
            # changed in recalculate_total
            if item.pk:
                item = self.items.get(pk=item.pk)

        try:
            self.validate(self.VALIDATE_BASE)
        except ValidationError:
            if item.pk:
                item.delete()
            raise

        return item

    def add_discount(self, discount, recalculate=True):
        """
        Add a discount instance to this order

        Removes the previous discount if a discount with this code has already
        been added to this order before.
        """

        discount.validate(self)

        try:
            self.applied_discounts.get(code=discount.code).delete()
        except ObjectDoesNotExist:
            # Don't increment used count when discount has already been applied
            discount.used += 1
            discount.save()

        instance = self.applied_discounts.create(
            code=discount.code,
            type=discount.type,
            name=discount.name,
            value=discount.value,
            currency=discount.currency,
            tax_class=discount.tax_class,
            config_json=discount.config_json,
            )

        if recalculate:
            self.recalculate_total()

        return instance

    @property
    def discount_remaining(self):
        """Remaining discount amount excl. tax"""
        return sum((d.remaining for d in self.applied_discounts.all()), Decimal('0.00'))

    def update_status(self, status, notes):
        """
        Update the order status
        """

        if status >= Order.CHECKOUT:
            if not self.items.count():
                raise ValidationError(_('Cannot proceed to checkout without order items.'),
                    code='order_empty')

        logger.info('Promoting %s to status %s' % (self, status))

        instance = OrderStatus(
            order=self,
            status=status,
            notes=notes)
        instance.save()

    def reload(self):
        """
        Return this order instance, reloaded from the database

        Used f.e. inside the payment processors when adding new payment records etc.
        """

        return self.__class__._default_manager.get(pk=self.id)


def validate_order_currencies(order):
    """Check whether order contains more than one or an invalid currency"""
    currencies = set(order.items.values_list('currency', flat=True))
    if currencies and (len(currencies) > 1 or order.currency not in currencies):
        raise ValidationError(_('Order contains more than one currency.'),
            code='multiple_currency')


def validate_order_stock_available(order):
    """Check whether enough stock is available for all selected products"""
    for item in order.items.all().select_related('variation'):
        if item.quantity > item.variation.available(exclude_order=order):
            raise ValidationError(_('Not enough stock available for %s.') % item.variation,
                code='insufficient_stock')


Order.register_validator(validate_order_currencies, Order.VALIDATE_BASE)
Order.register_validator(validate_order_stock_available, Order.VALIDATE_CART)


class OrderItem(models.Model):
    """Single order line item"""

    order = models.ForeignKey(Order, related_name='items')
    variation = models.ForeignKey(ProductVariation, verbose_name=_('product variation'))

    quantity = models.IntegerField(_('quantity'))

    currency = CurrencyField()
    _unit_price = models.DecimalField(_('unit price'),
        max_digits=18, decimal_places=10,
        help_text=_('Unit price excl. tax'))
    _unit_tax = models.DecimalField(_('unit tax'),
        max_digits=18, decimal_places=10)

    tax_rate = models.DecimalField(_('tax rate'), max_digits=10, decimal_places=2)
    tax_class = models.ForeignKey(TaxClass, verbose_name=_('tax class'),
        #blank=True, null=True, on_delete=models.SET_NULL)  # Only available in Django 1.3
        blank=True, null=True)

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

    data_json = models.TextField(_('data'), blank=True,
        help_text=_('JSON-encoded additional data about the order payment.'))
    data = JSONFieldDescriptor('data_json')

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
        return self.line_item_discount_excl_tax * (1+self.tax_rate/100)

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
    """
    Order status

    Stored in separate model so that the order status changes stay
    visible for analysis after the fact.
    """

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


class OrderPaymentManager(models.Manager):
    def pending(self):
        return self.filter(status=self.model.PENDING)

    def authorized(self):
        return self.filter(authorized__isnull=False)


class OrderPayment(models.Model):
    """
    Order payment

    Stores additional data from the payment interface for analysis
    and accountability.
    """

    PENDING = 10
    PROCESSED = 20
    AUTHORIZED = 30

    STATUS_CHOICES = (
        (PENDING, _('pending')),
        (PROCESSED, _('processed')),
        (AUTHORIZED, _('authorized')),
        )

    order = models.ForeignKey(Order, verbose_name=_('order'), related_name='payments')
    timestamp = models.DateTimeField(_('timestamp'), default=datetime.now)
    status = models.PositiveIntegerField(_('status'), choices=STATUS_CHOICES,
        default=PENDING)

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

    objects = OrderPaymentManager()

    def __unicode__(self):
        return u'%s of %s %.2f for %s' % (
            self.authorized and u'Authorized' or u'Not authorized',
            self.currency,
            self.amount,
            self.order,
            )

    def _recalculate_paid(self):
        paid = OrderPayment.objects.authorized().filter(
            order=self.order_id,
            currency=F('order__currency'),
            ).aggregate(total=Sum('amount'))['total'] or 0

        Order.objects.filter(id=self.order_id).update(paid=paid)

    def save(self, *args, **kwargs):
        super(OrderPayment, self).save(*args, **kwargs)
        self._recalculate_paid()

        if self.currency != self.order.currency:
            self.order.notes += u'\n' + _('Currency of payment %s does not match.') % self
            self.order.save()

    def delete(self, *args, **kwargs):
        super(OrderPayment, self).delete(*args, **kwargs)
        self._recalculate_paid()


class AppliedDiscount(DiscountBase):
    """
    Stores an applied discount, so that deletion of discounts does not
    affect orders.
    """

    order = models.ForeignKey(Order, related_name='applied_discounts',
        verbose_name=_('order'))
    code = models.CharField(_('code'), max_length=30) # We could make this a ForeignKey
                                                      # to Discount.code, but we do not
                                                      # want deletions to cascade to this
                                                      # table.
    remaining = models.DecimalField(_('remaining'),
        max_digits=18, decimal_places=10, default=0,
        help_text=_('Discount amount excl. tax remaining after discount has been applied.'))

    class Meta:
        ordering = ['type', 'name']
        verbose_name = _('applied discount')
        verbose_name_plural = _('applied discounts')
