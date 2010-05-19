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

from plata import plata_settings
from plata.contact.models import BillingShippingAddress, Contact
from plata.fields import CurrencyField
from plata.product.abstract import DiscountBase
from plata.product.models import Product, Discount, ProductVariation
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
    contact = models.ForeignKey(Contact, verbose_name=_('contact'))
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
        self.total = self.recalculate_items() + self.recalculate_shipping()

        if save:
            self.save()

    def recalculate_items(self):
        self.items_subtotal = self.items_tax = self.items_discount = 0

        items = list(self.items.all())

        for item in items:
            # Recalculate item stuff
            item._line_item_price = item.quantity * item._unit_price
            item._line_item_discount = 0

        self.recalculate_discounts(items)

        for item in items:
            taxable = item._line_item_price - (item._line_item_discount or 0)
            price = item.get_product_price()
            item._line_item_tax = taxable * price.tax_class.rate/100
            item.save()

            # Order stuff
            self.items_subtotal += item._line_item_price
            self.items_discount += item._line_item_discount or 0
            self.items_tax += item._line_item_tax

        return self.items_subtotal - self.items_discount + self.items_tax

    def recalculate_discounts(self, items):
        for applied in self.applied_discounts.all():
            applied.apply(self, items)

    def recalculate_shipping(self):
        #self.shipping_cost = self.shipping_discount = None
        self.shipping_tax = 0

        subtotal = 0

        if self.shipping_cost:
            subtotal += self.shipping_cost
        if self.shipping_discount:
            subtotal -= self.shipping_discount

        subtotal = max(subtotal, 0)

        # TODO move this into shipping processor
        self.shipping_tax = subtotal * Decimal('0.076')

        return subtotal + self.shipping_tax

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all()).quantize(Decimal('0.00'))

    @property
    def discount(self):
        return (self.subtotal - sum(item.discounted_subtotal for item in self.items.all())).quantize(Decimal('0.00'))

    @property
    def shipping(self):
        if plata_settings.PLATA_PRICE_INCLUDES_TAX:
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

    @property
    def is_paid(self):
        return self.balance_remaining <= 0

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
                'data': discount.data,
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
    variation = models.ForeignKey(ProductVariation)

    quantity = models.IntegerField(_('quantity'))

    currency = CurrencyField()
    _unit_price = models.DecimalField(_('unit price'),
        max_digits=18, decimal_places=10,
        help_text=_('Unit price excl. tax'))
    _unit_tax = models.DecimalField(_('unit tax'),
        max_digits=18, decimal_places=10)

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

    def get_product_price(self):
        return self.variation.product.get_price(currency=self.order.currency)

    @property
    def unit_price(self):
        if plata_settings.PLATA_PRICE_INCLUDES_TAX:
            return self._unit_price + self._unit_tax
        return self._unit_price

    @property
    def line_item_discount_excl_tax(self):
        return self._line_item_discount or 0

    @property
    def line_item_discount_incl_tax(self):
        price = self.get_product_price()
        return self.line_item_discount_excl_tax * (1+price.tax_class.rate/100)

    @property
    def line_item_discount(self):
        if plata_settings.PLATA_PRICE_INCLUDES_TAX:
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
        if plata_settings.PLATA_PRICE_INCLUDES_TAX:
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
    payment_method = models.CharField(_('payment method'), max_length=20, blank=True)
    transaction_id = models.CharField(_('transaction ID'), max_length=50, blank=True,
        help_text=_('Unique ID identifying this payment in the foreign system.'))

    authorized = models.DateTimeField(_('authorized'), blank=True, null=True,
        help_text=_('Point in time when payment has been authorized.'))

    data = models.TextField(_('data'), blank=True)
    data_json = JSONFieldDescriptor('data')

    class Meta:
        ordering = ('-timestamp',)
        verbose_name = _('order payment')
        verbose_name_plural = _('order payments')

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
