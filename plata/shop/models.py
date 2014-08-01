from __future__ import absolute_import, unicode_literals

from decimal import Decimal
import logging
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.urlresolvers import get_callable
from django.db import models
from django.db.models import F, ObjectDoesNotExist, Sum
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from django_countries.fields import CountryField

import plata
from plata.fields import CurrencyField, JSONField


logger = logging.getLogger('plata.shop.order')


@python_2_unicode_compatible
class TaxClass(models.Model):
    """
    Tax class, storing a tax rate

    TODO informational / advisory currency or country fields?
    """

    name = models.CharField(_('name'), max_length=100)
    rate = models.DecimalField(
        _('rate'), max_digits=10, decimal_places=2,
        help_text=_('Tax rate in percent.'))
    priority = models.PositiveIntegerField(
        _('priority'), default=0,
        help_text=_(
            'Used to order the tax classes in the administration interface.'))

    class Meta:
        ordering = ['-priority']
        verbose_name = _('tax class')
        verbose_name_plural = _('tax classes')

    def __str__(self):
        return self.name


class BillingShippingAddress(models.Model):
    """
    Abstract base class for all models storing a billing and a shipping
    address
    """

    ADDRESS_FIELDS = [
        'company', 'first_name', 'last_name', 'address',
        'zip_code', 'city', 'country']

    billing_company = models.CharField(
        _('company'), max_length=100, blank=True)
    billing_first_name = models.CharField(_('first name'), max_length=100)
    billing_last_name = models.CharField(_('last name'), max_length=100)
    billing_address = models.TextField(_('address'))
    billing_zip_code = models.CharField(
        plata.settings.PLATA_ZIP_CODE_LABEL, max_length=50)
    billing_city = models.CharField(_('city'), max_length=100)
    billing_country = CountryField(_('country'), blank=True)

    shipping_same_as_billing = models.BooleanField(
        _('shipping address equals billing address'),
        default=True)

    shipping_company = models.CharField(
        _('company'), max_length=100, blank=True)
    shipping_first_name = models.CharField(
        _('first name'), max_length=100, blank=True)
    shipping_last_name = models.CharField(
        _('last name'), max_length=100, blank=True)
    shipping_address = models.TextField(_('address'), blank=True)
    shipping_zip_code = models.CharField(
        plata.settings.PLATA_ZIP_CODE_LABEL, max_length=50, blank=True)
    shipping_city = models.CharField(_('city'), max_length=100, blank=True)
    shipping_country = CountryField(_('country'), blank=True)

    class Meta:
        abstract = True

    def addresses(self):
        """
        Return a ``dict`` containing a billing and a shipping address, taking
        into account the value of the ``shipping_same_as_billing`` flag
        """
        billing = dict(
            (f, getattr(self, 'billing_%s' % f)) for f in self.ADDRESS_FIELDS)

        if self.shipping_same_as_billing:
            shipping = billing
        else:
            shipping = dict(
                (f, getattr(self, 'shipping_%s' % f))
                for f in self.ADDRESS_FIELDS)

        return {'billing': billing, 'shipping': shipping}

    @classmethod
    def address_fields(cls, prefix=''):
        return ['%s%s' % (prefix, f) for f in cls.ADDRESS_FIELDS]


@python_2_unicode_compatible
class Order(BillingShippingAddress):
    """The main order model. Used for carts and orders alike."""
    #: Order object is a cart.
    CART = 10
    #: Checkout process has started.
    CHECKOUT = 20
    #: Order has been confirmed, but it not (completely) paid for yet.
    CONFIRMED = 30
    #: Order has been completely paid for.
    PAID = 40
    #: Order has been completed. Plata itself never sets this state,
    #: it is only meant for use by the shop owners.
    COMPLETED = 50

    STATUS_CHOICES = (
        (CART, _('Is a cart')),
        (CHECKOUT, _('Checkout process started')),
        (CONFIRMED, _('Order has been confirmed')),
        (PAID, _('Order has been paid')),
        (COMPLETED, _('Order has been completed')),
        )

    created = models.DateTimeField(_('created'), default=timezone.now)
    confirmed = models.DateTimeField(_('confirmed'), blank=True, null=True)
    user = models.ForeignKey(
        getattr(settings, 'AUTH_USER_MODEL', 'auth.User'),
        blank=True,
        null=True,
        verbose_name=_('user'),
        related_name='orders'
    )
    language_code = models.CharField(
        _('language'), max_length=10, default='', blank=True)
    status = models.PositiveIntegerField(
        _('status'), choices=STATUS_CHOICES, default=CART)

    _order_id = models.CharField(_('order ID'), max_length=20, blank=True)
    email = models.EmailField(_('e-mail address'))

    currency = CurrencyField()
    price_includes_tax = models.BooleanField(
        _('price includes tax'),
        default=plata.settings.PLATA_PRICE_INCLUDES_TAX)

    items_subtotal = models.DecimalField(
        _('subtotal'),
        max_digits=18, decimal_places=10, default=Decimal('0.00'))
    items_discount = models.DecimalField(
        _('items discount'),
        max_digits=18, decimal_places=10, default=Decimal('0.00'))
    items_tax = models.DecimalField(
        _('items tax'),
        max_digits=18, decimal_places=10, default=Decimal('0.00'))

    shipping_method = models.CharField(
        _('shipping method'),
        max_length=100, blank=True)
    shipping_cost = models.DecimalField(
        _('shipping cost'),
        max_digits=18, decimal_places=10, blank=True, null=True)
    shipping_discount = models.DecimalField(
        _('shipping discount'),
        max_digits=18, decimal_places=10, blank=True, null=True)
    shipping_tax = models.DecimalField(
        _('shipping tax'),
        max_digits=18, decimal_places=10, default=Decimal('0.00'))

    total = models.DecimalField(
        _('total'),
        max_digits=18, decimal_places=10, default=Decimal('0.00'))

    paid = models.DecimalField(
        _('paid'),
        max_digits=18, decimal_places=10, default=Decimal('0.00'),
        help_text=_('This much has been paid already.'))

    notes = models.TextField(_('notes'), blank=True)

    data = JSONField(
        _('data'), blank=True,
        help_text=_('JSON-encoded additional data about the order payment.'))

    class Meta:
        verbose_name = _('order')
        verbose_name_plural = _('orders')

    def __str__(self):
        return self.order_id

    def save(self, *args, **kwargs):
        """Sequential order IDs for completed orders."""
        if not self._order_id and self.status >= self.PAID:
            try:
                order = Order.objects.exclude(_order_id='').order_by(
                    '-_order_id')[0]
                latest = int(re.sub(r'[^0-9]', '', order._order_id))
            except (IndexError, ValueError):
                latest = 0

            self._order_id = 'O-%09d' % (latest + 1)
        super(Order, self).save(*args, **kwargs)
    save.alters_data = True

    @property
    def order_id(self):
        """
        Returns ``_order_id`` (if it has been set) or a generic ID for this
        order.
        """
        if self._order_id:
            return self._order_id
        return u'No. %d' % self.id

    def recalculate_total(self, save=True):
        """
        Recalculates totals, discounts, taxes.
        """

        items = list(self.items.all())
        shared_state = {}

        processor_classes = [
            get_callable(processor)
            for processor in plata.settings.PLATA_ORDER_PROCESSORS]

        for p in (cls(shared_state) for cls in processor_classes):
            p.process(self, items)

        if save:
            self.save()
            [item.save() for item in items]

    @property
    def subtotal(self):
        """
        Returns the order subtotal.
        """
        # TODO: What about shipping?
        return sum(
            (item.subtotal for item in self.items.all()),
            Decimal('0.00')).quantize(Decimal('0.00'))

    @property
    def discount(self):
        """
        Returns the discount total.
        """
        # TODO: What about shipping?
        return (
            sum(
                (item.subtotal for item in self.items.all()),
                Decimal('0.00')
            ) - sum(
                (item.discounted_subtotal for item in self.items.all()),
                Decimal('0.00')
            )
        ).quantize(Decimal('0.00'))

    @property
    def shipping(self):
        """
        Returns the shipping cost, with or without tax depending on this
        order's ``price_includes_tax`` field.
        """
        if self.price_includes_tax:
            if self.shipping_cost is None:
                return None

            return (
                self.shipping_cost
                - self.shipping_discount
                + self.shipping_tax)
        else:
            logger.error(
                'Shipping calculation with'
                ' PLATA_PRICE_INCLUDES_TAX=False is not implemented yet')
            raise NotImplementedError

    @property
    def tax(self):
        """
        Returns the tax total for this order, meaning tax on order items and
        tax on shipping.
        """
        return (self.items_tax + self.shipping_tax).quantize(Decimal('0.00'))

    @property
    def balance_remaining(self):
        """
        Returns the balance which needs to be paid by the customer to fully
        pay this order. This value is not necessarily the same as the order
        total, because there can be more than one order payment in principle.
        """
        return (self.total - self.paid).quantize(Decimal('0.00'))

    def is_paid(self):
        import warnings
        warnings.warn(
            'Order.is_paid() has been deprecated because its name is'
            ' misleading. Test for `order.status >= order.PAID` or'
            ' `not order.balance_remaining yourself.',
            DeprecationWarning, stacklevel=2)
        return self.balance_remaining <= 0

    #: This validator is always called; basic consistency checks such as
    #: whether the currencies in the order match should be added here.
    VALIDATE_BASE = 10
    #: A cart which fails the criteria added to the ``VALIDATE_CART`` group
    #: isn't considered a valid cart and the user cannot proceed to the
    #: checkout form. Stuff such as stock checking, minimal order total
    #: checking, or maximal items checking might be added here.
    VALIDATE_CART = 20
    #: This should not be used while registering a validator, it's mostly
    #: useful as an argument to :meth:`~plata.shop.models.Order.validate`
    #: when you want to run all validators.
    VALIDATE_ALL = 100

    VALIDATORS = {}

    @classmethod
    def register_validator(cls, validator, group):
        """
        Registers another order validator in a validation group

        A validator is a callable accepting an order (and only an order).

        There are several types of order validators:

        - Base validators are always called
        - Cart validators: Need to validate for a valid cart
        - Checkout validators: Need to validate in the checkout process
        """

        cls.VALIDATORS.setdefault(group, []).append(validator)

    def validate(self, group):
        """
        Validates this order

        The argument determines which order validators are called:

        - ``Order.VALIDATE_BASE``
        - ``Order.VALIDATE_CART``
        - ``Order.VALIDATE_CHECKOUT``
        - ``Order.VALIDATE_ALL``
        """

        for g in sorted(g for g in self.VALIDATORS.keys() if g <= group):
            for validator in self.VALIDATORS[g]:
                validator(self)

    def is_confirmed(self):
        """
        Returns ``True`` if this order has already been confirmed and
        therefore cannot be modified anymore.
        """
        return self.status >= self.CONFIRMED

    def modify_item(self, product, relative=None, absolute=None,
                    recalculate=True, data=None, item=None, force_new=False):
        """
        Updates order with the given product

        - ``relative`` or ``absolute``: Add/subtract or define order item
          amount exactly
        - ``recalculate``: Recalculate order after cart modification
          (defaults to ``True``)
        - ``data``: Additional data for the order item; replaces the contents
          of the JSON field if it is not ``None``. Pass an empty dictionary
          if you want to reset the contents.
        - ``item``: The order item which should be modified. Will be
          automatically detected using the product if unspecified.
        - ``force_new``: Force the creation of a new order item, even if the
          product exists already in the cart (especially useful if the
          product is configurable).

        Returns the ``OrderItem`` instance; if quantity is zero, the order
        item instance is deleted, the ``pk`` attribute set to ``None`` but
        the order item is returned anyway.
        """

        assert (relative is None) != (absolute is None),\
            'One of relative or absolute must be provided.'
        assert not (force_new and item),\
            'Cannot set item and force_new at the same time.'

        if self.is_confirmed():
            raise ValidationError(
                _('Cannot modify order once it has been confirmed.'),
                code='order_sealed')

        if item is None and not force_new:
            try:
                item = self.items.get(product=product)
            except self.items.model.DoesNotExist:
                # Ok, product does not exist in cart yet.
                pass
            except self.items.model.MultipleObjectsReturned:
                # Oops. Product already exists several times. Stay on the
                # safe side and add a new one instead of trying to modify
                # another.
                if not force_new:
                    raise ValidationError(
                        _(
                            'The product already exists several times in the'
                            ' cart, and neither item nor force_new were'
                            ' given.'),
                        code='multiple')

        if item is None:
            item = self.items.model(
                order=self,
                product=product,
                quantity=0,
                currency=self.currency,
            )

        if relative is not None:
            item.quantity += relative
        else:
            item.quantity = absolute

        if item.quantity > 0:
            try:
                price = product.get_price(
                    currency=self.currency,
                    orderitem=item)
            except ObjectDoesNotExist:
                logger.error(
                    u'No price could be found for %s with currency %s' % (
                        product, self.currency))

                raise ValidationError(
                    _('The price could not be determined.'),
                    code='unknown_price')

            if data is not None:
                item.data = data

            price.handle_order_item(item)
            product.handle_order_item(item)
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

    @property
    def discount_remaining(self):
        """Remaining discount amount excl. tax"""
        return self.applied_discounts.remaining()

    def update_status(self, status, notes):
        """
        Update the order status
        """

        if status >= Order.CHECKOUT:
            if not self.items.count():
                raise ValidationError(
                    _('Cannot proceed to checkout without order items.'),
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

        Used f.e. inside the payment processors when adding new payment
        records etc.
        """

        return self.__class__._default_manager.get(pk=self.id)

    def items_in_order(self):
        """
        Returns the item count in the order

        This is different from ``order.items.count()`` because it counts items,
        not distinct products.
        """
        return self.items.aggregate(q=Sum('quantity'))['q'] or 0


def validate_order_currencies(order):
    """Check whether order contains more than one or an invalid currency"""
    currencies = set(order.items.values_list('currency', flat=True))
    if (currencies
            and (len(currencies) > 1 or order.currency not in currencies)):
        raise ValidationError(
            _('Order contains more than one currency.'),
            code='multiple_currency')


Order.register_validator(validate_order_currencies, Order.VALIDATE_BASE)


@python_2_unicode_compatible
class OrderItem(models.Model):
    """Single order line item"""

    order = models.ForeignKey(Order, related_name='items')
    product = models.ForeignKey(
        plata.settings.PLATA_SHOP_PRODUCT,
        verbose_name=_('product'),
        blank=True, null=True, on_delete=models.SET_NULL)

    name = models.CharField(_('name'), max_length=100, blank=True)
    sku = models.CharField(_('SKU'), max_length=100, blank=True)

    quantity = models.IntegerField(_('quantity'))

    currency = CurrencyField()
    _unit_price = models.DecimalField(
        _('unit price'),
        max_digits=18, decimal_places=10,
        help_text=_('Unit price excl. tax'))
    _unit_tax = models.DecimalField(
        _('unit tax'),
        max_digits=18, decimal_places=10)

    tax_rate = models.DecimalField(
        _('tax rate'),
        max_digits=10, decimal_places=2)
    tax_class = models.ForeignKey(
        TaxClass, verbose_name=_('tax class'),
        blank=True, null=True, on_delete=models.SET_NULL)

    is_sale = models.BooleanField(_('is sale'))

    _line_item_price = models.DecimalField(
        _('line item price'),
        max_digits=18, decimal_places=10, default=0,
        help_text=_('Line item price excl. tax'))
    _line_item_discount = models.DecimalField(
        _('line item discount'),
        max_digits=18, decimal_places=10,
        blank=True, null=True,
        help_text=_('Discount excl. tax'))

    _line_item_tax = models.DecimalField(
        _('line item tax'),
        max_digits=18, decimal_places=10, default=0)

    data = JSONField(
        _('data'), blank=True,
        help_text=_('JSON-encoded additional data about the order payment.'))

    class Meta:
        ordering = ('product',)
        verbose_name = _('order item')
        verbose_name_plural = _('order items')

    def __str__(self):
        return _('%(quantity)s of %(name)s') % {
            'quantity': self.quantity,
            'name': self.name,
        }

    @property
    def unit_price(self):
        if self.order.price_includes_tax:
            return self._unit_price + self._unit_tax
        return self._unit_price

    @property
    def line_item_discount_excl_tax(self):
        return self._line_item_discount or 0

    @property
    def line_item_discount_incl_tax(self):
        return self.line_item_discount_excl_tax * (1 + self.tax_rate / 100)

    @property
    def line_item_discount(self):
        if self.order.price_includes_tax:
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
        if self.order.price_includes_tax:
            return self.discounted_subtotal_incl_tax
        else:
            return self.discounted_subtotal_excl_tax


@python_2_unicode_compatible
class OrderStatus(models.Model):
    """
    Order status

    Stored in separate model so that the order status changes stay
    visible for analysis after the fact.
    """

    order = models.ForeignKey(Order, related_name='statuses')
    created = models.DateTimeField(_('created'), default=timezone.now)
    status = models.PositiveIntegerField(
        _('status'), max_length=20, choices=Order.STATUS_CHOICES)
    notes = models.TextField(_('notes'), blank=True)

    class Meta:
        ordering = ('created', 'id')
        verbose_name = _('order status')
        verbose_name_plural = _('order statuses')

    def __str__(self):
        return _('Status %(status)s for %(order)s') % {
            'status': self.get_status_display(),
            'order': self.order,
        }

    def save(self, *args, **kwargs):
        super(OrderStatus, self).save(*args, **kwargs)
        self.order.status = self.status
        if self.status == Order.CONFIRMED:
            self.order.confirmed = timezone.now()
        elif self.status > Order.CONFIRMED and not self.order.confirmed:
            self.order.confirmed = timezone.now()
        elif self.status < Order.CONFIRMED:
            # Ensure that the confirmed date is not set
            self.order.confirmed = None
        self.order.save()
    save.alters_data = True


class OrderPaymentManager(models.Manager):
    def pending(self):
        return self.filter(status=self.model.PENDING)

    def authorized(self):
        return self.filter(authorized__isnull=False)


@python_2_unicode_compatible
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

    order = models.ForeignKey(
        Order, verbose_name=_('order'), related_name='payments')
    timestamp = models.DateTimeField(_('timestamp'), default=timezone.now)
    status = models.PositiveIntegerField(
        _('status'), choices=STATUS_CHOICES, default=PENDING)

    currency = CurrencyField()
    amount = models.DecimalField(_('amount'), max_digits=10, decimal_places=2)
    payment_module_key = models.CharField(
        _('payment module key'),
        max_length=20,
        help_text=_(
            'Machine-readable identifier for the payment module used.'))
    payment_module = models.CharField(
        _('payment module'), max_length=50,
        blank=True,
        help_text=_('For example \'Cash on delivery\', \'PayPal\', ...'))
    payment_method = models.CharField(
        _('payment method'), max_length=50,
        blank=True,
        help_text=_(
            'For example \'MasterCard\', \'VISA\' or some other card.'))
    transaction_id = models.CharField(
        _('transaction ID'), max_length=50,
        blank=True,
        help_text=_(
            'Unique ID identifying this payment in the foreign system.'))

    authorized = models.DateTimeField(
        _('authorized'), blank=True, null=True,
        help_text=_('Point in time when payment has been authorized.'))

    notes = models.TextField(_('notes'), blank=True)

    data = JSONField(
        _('data'), blank=True,
        help_text=_('JSON-encoded additional data about the order payment.'))

    class Meta:
        ordering = ('-timestamp',)
        verbose_name = _('order payment')
        verbose_name_plural = _('order payments')

    objects = OrderPaymentManager()

    def __str__(self):
        return _(
            '%(authorized)s of %(currency)s %(amount).2f for %(order)s'
        ) % {
            'authorized': (
                self.authorized and _('Authorized') or _('Not authorized')),
            'currency': self.currency,
            'amount': self.amount,
            'order': self.order,
        }

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
            self.order.notes += (
                u'\n' + _('Currency of payment %s does not match.') % self)
            self.order.save()
    save.alters_data = True

    def delete(self, *args, **kwargs):
        super(OrderPayment, self).delete(*args, **kwargs)
        self._recalculate_paid()
    delete.alters_data = True


@python_2_unicode_compatible
class PriceBase(models.Model):
    """
    Price for a given product, currency, tax class and time period

    Prices should not be changed or deleted but replaced by more recent
    prices. (Deleting old prices does not hurt, but the price history cannot
    be reconstructed anymore if you'd need it.)

    The concrete implementation needs to provide a foreign key to the
    product model.
    """

    class Meta:
        abstract = True
        ordering = ['-id']
        verbose_name = _('price')
        verbose_name_plural = _('prices')

    currency = CurrencyField()
    _unit_price = models.DecimalField(
        _('unit price'),
        max_digits=18, decimal_places=10)
    tax_included = models.BooleanField(
        _('tax included'),
        help_text=_('Is tax included in given unit price?'),
        default=plata.settings.PLATA_PRICE_INCLUDES_TAX)
    tax_class = models.ForeignKey(
        TaxClass, verbose_name=_('tax class'), related_name='+')

    def __str__(self):
        return '%s %.2f' % (self.currency, self.unit_price)

    def __cmp__(self, other):
        return int(
            (self.unit_price_excl_tax - other.unit_price_excl_tax) * 100)

    def __hash__(self):
        return int(self.unit_price_excl_tax * 100)

    def handle_order_item(self, item):
        """
        Set price data on the ``OrderItem`` passed
        """
        item._unit_price = self.unit_price_excl_tax
        item._unit_tax = self.unit_tax
        item.tax_rate = self.tax_class.rate
        item.tax_class = self.tax_class
        item.is_sale = False  # Hardcoded; override in your own price class

    @property
    def unit_tax(self):
        return self.unit_price_excl_tax * (self.tax_class.rate / 100)

    @property
    def unit_price_incl_tax(self):
        if self.tax_included:
            return self._unit_price
        return self._unit_price * (1 + self.tax_class.rate / 100)

    @property
    def unit_price_excl_tax(self):
        if not self.tax_included:
            return self._unit_price
        return self._unit_price / (1 + self.tax_class.rate / 100)

    @property
    def unit_price(self):
        # TODO Fix this. We _should_ use shop.price_includes_tax here,
        # but there's no request and no order around...
        return self.unit_price_incl_tax
