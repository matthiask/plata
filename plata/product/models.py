"""
This module contains the core classes needed to work with products in
Plata. The core classes should be used directly and not replaced even
if you provide your own product model implementation.

The core models are:

* ``TaxClass``
* ``ProductPrice``

(FIXME: They aren't enough abstract yet. Product, ProductVariation,
ProductImage, OptionGroup and Option should be moved somewhere else.)
"""

from datetime import date, datetime

from django.db import models
from django.db.models import Q, Count, signals

from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _

import plata
from plata.compat import product as itertools_product
from plata.fields import CurrencyField


class TaxClass(models.Model):
    """
    Tax class, storing a tax rate

    TODO informational / advisory currency or country fields?
    """

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


class CategoryManager(models.Manager):
    def active(self):
        return self.filter(is_active=True)

    def public(self):
        return self.filter(is_active=True, is_internal=False)


class Category(models.Model):
    """
    Categories are both used for external and internal organization of products.
    If the ``is_internal`` flag is set, categories will never appear in the shop
    but can be used f.e. to group discountable products together.
    """

    is_active = models.BooleanField(_('is active'), default=True)
    is_internal = models.BooleanField(_('is internal'), default=False,
        help_text=_('Only used to internally organize products, f.e. for discounting.'))

    name = models.CharField(_('name'), max_length=100)
    slug = models.SlugField(_('slug'), unique=True)
    ordering = models.PositiveIntegerField(_('ordering'), default=0)
    description = models.TextField(_('description'), blank=True)

    parent = models.ForeignKey('self', blank=True, null=True,
        limit_choices_to={'parent__isnull': True},
        related_name='children', verbose_name=_('parent'))

    class Meta:
        ordering = ['parent__ordering', 'parent__name', 'ordering', 'name']
        verbose_name = _('category')
        verbose_name_plural = _('categories')

    objects = CategoryManager()

    def __unicode__(self):
        if self.parent_id:
            return u'%s - %s' % (self.parent, self.name)
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('plata_category_detail', (), {'object_id': self.pk})


class ProductPriceManager(models.Manager):
    def active(self):
        return self.filter(
            Q(is_active=True),
            Q(valid_from__lte=date.today()),
            Q(valid_until__isnull=True) | Q(valid_until__gte=date.today()))


class ProductPrice(models.Model):
    """
    Price for a given product, currency, tax class and time period

    Prices should not be changed or deleted but replaced by more recent prices.
    (Deleting old prices does not hurt, but the price history cannot be
    reconstructed anymore if you'd need it.)

    TODO rename this to Price and move to plata.shop.models?
    """

    # FIXME do not hardcode price relation
    product = models.ForeignKey('product.Product', verbose_name=_('product'),
        related_name='prices')
    currency = CurrencyField()
    _unit_price = models.DecimalField(_('unit price'), max_digits=18, decimal_places=10)
    tax_included = models.BooleanField(_('tax included'),
        help_text=_('Is tax included in given unit price?'),
        default=plata.settings.PLATA_PRICE_INCLUDES_TAX)
    tax_class = models.ForeignKey(TaxClass, verbose_name=_('tax class'))

    is_active = models.BooleanField(_('is active'), default=True)
    valid_from = models.DateField(_('valid from'), default=date.today)
    valid_until = models.DateField(_('valid until'), blank=True, null=True)

    is_sale = models.BooleanField(_('is sale'), default=False,
        help_text=_('Set this if this price is a sale price. Whether the sale is temporary or not does not matter.'))

    class Meta:
        get_latest_by = 'id'
        ordering = ['-valid_from']
        verbose_name = _('product price')
        verbose_name_plural = _('product prices')

    objects = ProductPriceManager()

    def __unicode__(self):
        return u'%s %.2f' % (self.currency, self.unit_price)

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
        if plata.settings.PLATA_PRICE_INCLUDES_TAX:
            return self.unit_price_incl_tax
        else:
            return self.unit_price_excl_tax


def flush_price_cache(instance, **kwargs):
    instance.product.flush_price_cache()
signals.post_save.connect(flush_price_cache, sender=ProductPrice)
signals.post_delete.connect(flush_price_cache, sender=ProductPrice)
