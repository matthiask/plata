from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy as _

from plata import plata_settings


class TaxClass(models.Model):
    name = models.CharField(_('name'), max_length=100)
    rate = models.DecimalField(_('rate'), max_digits=10, decimal_places=2)
    priority = models.PositiveIntegerField(_('priority'), default=0,
        help_text = _('Used to order the tax classes in the administration interface.'))

    class Meta:
        ordering = ['-priority']
        verbose_name = _('tax class')
        verbose_name_plural = _('tax classes')

    def __unicode__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(_('name'), max_length=100)
    description = models.TextField(_('description'), blank=True)

    class Meta:
        verbose_name = _('product')
        verbose_name_plural = _('products')

    def __unicode__(self):
        return self.name

    def get_price(self, **kwargs):
        return self.prices.filter(**kwargs).latest()


def get_default_taxclass():
    try:
        return TaxClass.objects.all()[0]
    except IndexError:
        return None


class ProductPrice(models.Model):
    product = models.ForeignKey(Product, verbose_name=_('product'),
        related_name='prices')
    created = models.DateTimeField(_('created'), default=datetime.now)
    tax_class = models.ForeignKey(TaxClass, verbose_name=_('tax class'),
        default=get_default_taxclass)

    _unit_price = models.DecimalField(_('unit price'), max_digits=18, decimal_places=10)
    tax_included = models.BooleanField(_('tax included'),
        help_text=_('Is tax included in given unit price?'),
        default=plata_settings.PLATA_PRICE_INCLUDES_TAX)
    currency = models.CharField(_('currency'), max_length=10)

    class Meta:
        get_latest_by = 'id'
        ordering = ['-id']
        verbose_name = _('product price')
        verbose_name_plural = _('product prices')

    @property
    def unit_tax(self):
        return self.unit_price_excl_tax * (self.tax_class.rate/100)

    @property
    def unit_price_incl_tax(self):
        if self.tax_included:
            return self._unit_price
        return self._unit_price * (1+self.tax_class.rate/100)

    @property
    def unit_price_excl_tax(self):
        if not self.tax_included:
            return self._unit_price
        return self._unit_price / (1+self.tax_class.rate/100)

    @property
    def unit_price(self):
        if plata_settings.PLATA_PRICE_INCLUDES_TAX:
            return self.unit_price_incl_tax
        else:
            return self.unit_price_excl_tax


class ProductImage(models.Model):
    product = models.ForeignKey(Product, verbose_name=_('product'),
        related_name='images')
    image = models.ImageField(_('image'),
        upload_to=lambda instance, filename: '%s/%s' % (instance.product.slug, filename))
    ordering = models.PositiveIntegerField(_('ordering'), default=0)

    class Meta:
        ordering = ['ordering']
        verbose_name = _('product image')
        verbose_name_plural = _('product images')


class DiscountBase(models.Model):
    AMOUNT_EXCL_TAX = 10
    AMOUNT_INCL_TAX = 20
    PERCENTAGE = 30

    TYPE_CHOICES = (
        (AMOUNT_EXCL_TAX, _('amount excl. tax')),
        (AMOUNT_INCL_TAX, _('amount incl. tax')),
        (PERCENTAGE, _('percentage')),
        )

    name = models.CharField(_('name'), max_length=100)

    type = models.PositiveIntegerField(_('type'), choices=TYPE_CHOICES)
    value = models.DecimalField(_('value'), max_digits=10, decimal_places=2)

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.name

    def apply(self, order, items, **kwargs):
        if not items:
            return

        if self.type == self.AMOUNT_EXCL_TAX:
            self.apply_amount_discount(order, items, tax_included=False)
        elif self.type == self.AMOUNT_INCL_TAX:
            self.apply_amount_discount(order, items, tax_included=True)
        elif self.type == self.PERCENTAGE:
            self.apply_percentage_discount(order, items)
        else:
            raise NotImplementedError, 'Unknown discount type %s' % self.type

    def apply_amount_discount(self, order, items, tax_included):
        if tax_included:
            tax_rate = items[0].get_price().tax_class.rate
            discount = self.value / (1 + tax_rate/100)
        else:
            discount = self.value

        items_subtotal = sum([item._line_item_price for item in items], 0)

        if items_subtotal < discount:
            remaining = discount - items_subtotal
            discount = items_subtotal

            # TODO do something with remaining

        for item in items:
            item._line_item_discount = item._line_item_price / items_subtotal * discount

    def apply_percentage_discount(self, order, items):
        factor = self.value / 100

        for item in items:
            item._line_item_discount = item._line_item_price * factor


class Discount(DiscountBase):
    key = models.CharField(_('key'), max_length=30, unique=True)

    class Meta:
        verbose_name = _('discount')
        verbose_name_plural = _('discounts')
