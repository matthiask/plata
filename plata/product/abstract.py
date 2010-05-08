# abstract product base models

from datetime import date, datetime

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from plata import plata_settings, shop_instance
from plata.fields import CurrencyField
from plata.utils import JSONFieldDescriptor


class TaxClass(models.Model):
    name = models.CharField(_('name'), max_length=100)
    rate = models.DecimalField(_('rate'), max_digits=10, decimal_places=2)
    priority = models.PositiveIntegerField(_('priority'), default=0,
        help_text = _('Used to order the tax classes in the administration interface.'))

    class Meta:
        abstract = True
        ordering = ['-priority']
        verbose_name = _('tax class')
        verbose_name_plural = _('tax classes')

    def __unicode__(self):
        return self.name


class Category(models.Model):
    is_active = models.BooleanField(_('is active'), default=True)
    is_internal = models.BooleanField(_('is internal'), default=False,
        help_text=_('Only used to internally organize products, f.e. for discounting.'))

    name = models.CharField(_('name'), max_length=100)
    slug = models.SlugField(_('slug'), unique=True)
    ordering = models.PositiveIntegerField(_('ordering'), default=0)
    description = models.TextField(_('description'), blank=True)

    parent = models.ForeignKey('self', blank=True, null=True,
        related_name='children', verbose_name=_('parent'))

    class Meta:
        abstract = True
        ordering = ['ordering', 'name']
        verbose_name = _('category')
        verbose_name_plural = _('categories')

    def __unicode__(self):
        if self.parent_id:
            return u'%s - %s' % (self.parent, self.name)
        return self.name


class Product(models.Model):
    is_active = models.BooleanField(_('is active'), default=True)
    name = models.CharField(_('name'), max_length=100)
    slug = models.SlugField(_('slug'), unique=True)
    ordering = models.PositiveIntegerField(_('ordering'), default=0)
    sku = models.CharField(_('SKU'), max_length=100, blank=True)

    class Meta:
        abstract = True
        ordering = ['ordering', 'name']
        verbose_name = _('product')
        verbose_name_plural = _('products')

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = self.slug
        super(Product, self).save(*args, **kwargs)

    @models.permalink
    def get_absolute_url(self):
        return ('plata_product_detail', (), {'object_id': self.pk})

    def get_price(self, **kwargs):
        return self.prices.filter(
            Q(is_active=True),
            Q(valid_from__lte=date.today()),
            Q(valid_until__isnull=True) | Q(valid_until__gte=date.today()),
            ).filter(**kwargs).latest()


class ProductPrice(models.Model):
    currency = CurrencyField()
    _unit_price = models.DecimalField(_('unit price'), max_digits=18, decimal_places=10)
    tax_included = models.BooleanField(_('tax included'),
        help_text=_('Is tax included in given unit price?'),
        default=plata_settings.PLATA_PRICE_INCLUDES_TAX)

    is_active = models.BooleanField(_('is active'), default=True)
    valid_from = models.DateField(_('valid from'), default=date.today)
    valid_until = models.DateField(_('valid until'), blank=True, null=True)

    is_sale = models.BooleanField(_('is sale'), default=False,
        help_text=_('Set this if this price is a sale price. Whether the sale is temporary or not does not matter.'))

    class Meta:
        abstract = True
        get_latest_by = 'id'
        ordering = ['-valid_from']
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

    data = models.TextField(_('data'), blank=True)
    data_json = JSONFieldDescriptor('data')

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.name

    def eligible_products(self, queryset=None):
        if not queryset:
            queryset = shop_instance().product_model._default_manager.all()

        data = self.data_json
        if 'eligible_filter' in data:
            queryset = queryset.filter(**dict((str(k), v) for k, v in data['eligible_filter'].items()))

        return queryset

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
        eligible_products = self.eligible_products().values_list('id', flat=True)

        eligible_items = [item for item in items if item.variation.product_id in eligible_products]

        if tax_included:
            tax_rate = items[0].get_price().tax_class.rate
            discount = self.value / (1 + tax_rate/100)
        else:
            discount = self.value

        items_subtotal = sum([item.discounted_subtotal_excl_tax for item in eligible_items], 0)

        if items_subtotal < discount:
            remaining = discount - items_subtotal
            discount = items_subtotal

            # TODO do something with remaining

        for item in eligible_items:
            item._line_item_discount += item.discounted_subtotal_excl_tax / items_subtotal * discount

    def apply_percentage_discount(self, order, items):
        eligible_products = self.eligible_products().values_list('id', flat=True)

        factor = self.value / 100

        for item in items:
            if item.variation.product_id not in eligible_products:
                continue

            item._line_item_discount += item.discounted_subtotal_excl_tax * factor

