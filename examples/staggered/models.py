import sys

from django.db import models
from django.utils.translation import ugettext_lazy as _

import plata
from plata.product.models import ProductBase, register_price_cache_handlers
from plata.shop.models import Price, PriceManager


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
        if orderitem is not None:
            try:
                return self.prices.active().exclude(
                    from_quantity__gt=orderitem.quantity,
                    ).order_by('-from_quantity')[0]
            except IndexError:
                # Fall back to default handling
                pass

        return self.prices.active()

        return self.prices.determine_price(self, currency)

class ProductPrice(Price):
    product = models.ForeignKey(Product, verbose_name=_('product'),
        related_name='prices')
    from_quantity = models.IntegerField(_('From quantity'), default=0)

    class Meta:
        app_label = 'product'
        get_latest_by = 'id'
        ordering = ['from_quantity', '-valid_from']
        verbose_name = _('price')
        verbose_name_plural = _('prices')

    objects = PriceManager()

register_price_cache_handlers(ProductPrice)
