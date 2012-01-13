import sys

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy as _

import plata
from plata.product.models import ProductBase, register_price_cache_handlers
from plata.shop.models import PriceBase


class Product(ProductBase):
    """(Nearly) the simplest product model ever"""

    is_active = models.BooleanField(_('is active'), default=True)
    name = models.CharField(_('name'), max_length=100)
    slug = models.SlugField(_('slug'), unique=True)
    ordering = models.PositiveIntegerField(_('ordering'), default=0)

    description = models.TextField(_('description'), blank=True)

    class Meta:
        app_label = 'product'
        ordering = ['ordering', 'name']
        verbose_name = _('product')
        verbose_name_plural = _('products')

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('plata_product_detail', (), {'object_id': self.pk})

    def get_price(self, currency=None, orderitem=None):
        if currency is None:
            currency = (orderitem.currency if orderitem else
                plata.shop_instance().default_currency())

        possible = self.prices.filter(currency=currency)

        if orderitem is not None:
            possible = possible.filter(
                from_quantity__lte=orderitem.quantity).order_by('-from_quantity')
        else:
            possible = possible.order_by('from_quantity')

        try:
            return possible[0]
        except IndexError:
            raise possible.model.DoesNotExist

    def get_prices(self):
        # Do nothing.
        pass


class ProductPrice(PriceBase):
    product = models.ForeignKey(Product, verbose_name=_('product'),
        related_name='prices')
    from_quantity = models.IntegerField(_('From quantity'), default=0)

    class Meta:
        app_label = 'product'
        get_latest_by = 'id'
        ordering = ['from_quantity']
        verbose_name = _('price')
        verbose_name_plural = _('prices')

register_price_cache_handlers(ProductPrice)
