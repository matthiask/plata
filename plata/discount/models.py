from datetime import date
from decimal import Decimal
import random

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import ObjectDoesNotExist, Q
from django.utils.translation import ugettext_lazy as _

import plata
from plata.fields import CurrencyField
from plata.shop.models import TaxClass, Order
from plata.utils import JSONFieldDescriptor


class DiscountBase(models.Model):
    """Base class for discounts and applied discounts"""

    AMOUNT_VOUCHER_EXCL_TAX = 10
    AMOUNT_VOUCHER_INCL_TAX = 20
    PERCENTAGE_VOUCHER = 30
    MEANS_OF_PAYMENT = 40

    TYPE_CHOICES = (
        (AMOUNT_VOUCHER_EXCL_TAX,
            _('amount voucher excl. tax (reduces total tax on order)')),
        (AMOUNT_VOUCHER_INCL_TAX,
            _('amount voucher incl. tax (reduces total tax on order)')),
        (PERCENTAGE_VOUCHER,
            _('percentage voucher (reduces total tax on order)')),
        (MEANS_OF_PAYMENT,
            _('means of payment (does not change total tax on order)')),
        )

    #: You can add and remove options at will, except for 'all': This option
    #: must always be available, and it cannot have any form fields
    CONFIG_OPTIONS = [
        ('all', {
            'title': _('All products'),
            }),
        ('exclude_sale', {
            'title': _('Exclude sale prices'),
            'orderitem_query': lambda **values: Q(is_sale=False),
            }),
        ]

    name = models.CharField(_('name'), max_length=100)

    type = models.PositiveIntegerField(_('type'), choices=TYPE_CHOICES)
    value = models.DecimalField(_('value'), max_digits=18, decimal_places=10)

    currency = CurrencyField(blank=True, null=True,
        help_text=_('Only required for amount discounts.'))
    tax_class = models.ForeignKey(TaxClass, verbose_name=_('tax class'),
        blank=True, null=True, help_text=_('Only required for amount discounts incl. tax.'))

    config_json = models.TextField(_('configuration'), blank=True,
        help_text=_('If you edit this field directly, changes below will be ignored.'))
    config = JSONFieldDescriptor('config_json')

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.full_clean()
        super(DiscountBase, self).save(*args, **kwargs)

    def clean(self):
        if self.type == self.PERCENTAGE_VOUCHER:
            if self.currency or self.tax_class:
                raise ValidationError(_('Percentage discounts cannot have currency and tax class set.'))
        elif self.type == self.AMOUNT_VOUCHER_EXCL_TAX:
            if not self.currency:
                raise ValidationError(_('Amount discounts excl. tax need a currency.'))
            if self.tax_class:
                raise ValidationError(_('Amount discounts excl. tax cannot have tax class set.'))
        elif self.type == self.AMOUNT_VOUCHER_INCL_TAX:
            if not (self.currency and self.tax_class):
                raise ValidationError(_('Amount discounts incl. tax need a currency and a tax class.'))
        elif self.type == self.MEANS_OF_PAYMENT:
            if not self.currency:
                raise ValidationError(_('Means of payment need a currency.'))
            if self.tax_class:
                raise ValidationError(_('Means of payment cannot have tax class set.'))
        else:
            raise ValidationError(_('Unknown discount type.'))

    def _eligible_products(self, order, items):
        """
        Return a list of products which are eligible for discounting using
        the discount configuration.
        """

        product_model = plata.product_model()

        products = product_model._default_manager.filter(
            id__in=[item.product_id for item in items])
        orderitems = order.items.model._default_manager.filter(
            id__in=[item.id for item in items])

        for key, parameters in self.config.items():
            parameters = dict((str(k), v) for k, v in parameters.items())

            cfg = dict(self.CONFIG_OPTIONS)[key]

            if 'product_query' in cfg:
                products = products.filter(cfg['product_query'](**parameters))
            if 'orderitem_query' in cfg:
                orderitems = orderitems.filter(cfg['orderitem_query'](**parameters))

        return products.filter(id__in=orderitems.values('product_id'))

    def apply(self, order, items, **kwargs):
        if not items:
            return

        if self.type == self.AMOUNT_VOUCHER_EXCL_TAX:
            self._apply_amount_discount(order, items, tax_included=False)
        elif self.type == self.AMOUNT_VOUCHER_INCL_TAX:
            self._apply_amount_discount(order, items, tax_included=True)
        elif self.type == self.PERCENTAGE_VOUCHER:
            self._apply_percentage_discount(order, items)
        elif self.type == self.MEANS_OF_PAYMENT:
            self._apply_means_of_payment(order, items)
        else:
            raise NotImplementedError, 'Unknown discount type %s' % self.type

    def _apply_amount_discount(self, order, items, tax_included):
        """
        Apply amount discount evenly to all eligible order items

        Aggregates remaining discount (if discount is bigger than order total)
        """

        eligible_products = self._eligible_products(order, items).values_list('id', flat=True)
        eligible_items = [item for item in items if item.product_id in eligible_products]

        if tax_included:
            discount = self.value / (1 + self.tax_class.rate/100)
        else:
            discount = self.value

        items_subtotal = sum([item.discounted_subtotal_excl_tax for item in eligible_items],
            Decimal('0.00'))

        # Don't allow bigger discounts than the items subtotal
        if discount > items_subtotal:
            self.remaining = discount - items_subtotal
            self.save()
            discount = items_subtotal

        for item in eligible_items:
            item._line_item_discount += item.discounted_subtotal_excl_tax / items_subtotal * discount

    def _apply_means_of_payment(self, order, items):
        self._apply_amount_discount(order, items, tax_included=False)

    def _apply_percentage_discount(self, order, items):
        """
        Apply percentage discount evenly to all eligible order items
        """

        eligible_products = self._eligible_products(order, items).values_list('id', flat=True)

        factor = self.value / 100

        for item in items:
            if item.product_id not in eligible_products:
                continue

            item._line_item_discount += item.discounted_subtotal_excl_tax * factor


# Nearly all letters and digits, excluding those which can be easily confounded
RANDOM_CODE_CHARACTERS = '23456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ'

def generate_random_code():
    return u''.join(random.sample(RANDOM_CODE_CHARACTERS, 10))


class Discount(DiscountBase):
    code = models.CharField(_('code'), max_length=30, unique=True,
        default=generate_random_code)

    is_active = models.BooleanField(_('is active'), default=True)
    valid_from = models.DateField(_('valid from'), default=date.today)
    valid_until = models.DateField(_('valid until'), blank=True, null=True)

    allowed_uses = models.IntegerField(_('number of allowed uses'),
        blank=True, null=True,
        help_text=_('Leave empty if there is no limit on the number of uses of this discount.'))
    used = models.IntegerField(_('number of times already used'), default=0)

    class Meta:
        verbose_name = _('discount')
        verbose_name_plural = _('discounts')

    def validate(self, order):
        """
        Validate whether this discount can be applied at all on the given order
        """

        messages = []
        if not self.is_active:
            messages.append(_('Discount is inactive.'))

        today = date.today()
        if today < self.valid_from:
            messages.append(_('Discount is not active yet.'))
        if self.valid_until and today > self.valid_until:
            messages.append(_('Discount is expired.'))

        if self.allowed_uses and self.used >= self.allowed_uses:
            messages.append(_('Allowed uses for this discount has already been reached.'))

        if (self.currency != order.currency and self.type in (
                self.AMOUNT_VOUCHER_EXCL_TAX,
                self.AMOUNT_VOUCHER_INCL_TAX,
                self.MEANS_OF_PAYMENT)):
            messages.append(_('Discount and order currencies do not match.'))

        if messages:
            raise ValidationError(messages)

        return True

    def add_to(self, order, recalculate=True):
        """
        Add discount to passed order

        Removes the previous discount if a discount with this code has already
        been added to the order before.
        """

        self.validate(order)

        try:
            order.applied_discounts.get(code=self.code).delete()
        except ObjectDoesNotExist:
            # Don't increment used count when discount has already been applied
            self.used += 1
            self.save()

        instance = order.applied_discounts.create(
            code=self.code,
            type=self.type,
            name=self.name,
            value=self.value,
            currency=self.currency,
            tax_class=self.tax_class,
            config_json=self.config_json,
            )

        if recalculate:
            order.recalculate_total()

        return instance


class AppliedDiscountManager(models.Manager):
    """
    Default manager for the ``AppliedDiscount`` model
    """

    def remaining(self, order=None):
        """
        Calculate remaining discount excl. tax

        Can either be used as related manager::

            order.applied_discounts.remaining()

        or directly::

            AppliedDiscount.objects.remaining(order)
        """

        queryset = self.all()
        if order:
            queryset = queryset.filter(order=order)

        return sum((d.remaining for d in queryset), Decimal('0.00'))


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

    objects = AppliedDiscountManager()
