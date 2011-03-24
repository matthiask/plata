import sys

from django.db import models
from django.db.models import signals
from django.utils.translation import ugettext_lazy as _

import plata
from plata.reporting.notifications import ConsoleHandler
from plata.shop.models import Price, PriceManager


handler = ConsoleHandler.register(stream=sys.stderr)


class ProductPrice(Price):
    product = models.ForeignKey('product.Product', verbose_name=_('product'),
        related_name='prices')

    class Meta:
        app_label = 'product'
        get_latest_by = 'id'
        ordering = ['-valid_from']
        verbose_name = _('price')
        verbose_name_plural = _('prices')

    objects = PriceManager()


class ProductManager(models.Manager):
    def active(self):
        return self.filter(is_active=True)


class Product(models.Model):
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

    objects = ProductManager()

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        super(Product, self).save(*args, **kwargs)
        self.flush_price_cache()

    @models.permalink
    def get_absolute_url(self):
        return ('plata_product_detail', (), {'object_id': self.pk})

    def get_price(self, currency=None):
        return self.prices.determine_price(self, currency)

    def get_prices(self):
        return self.prices.determine_prices(self)

    def flush_price_cache(self):
        self.prices.flush_price_cache(self)


def flush_price_cache(instance, **kwargs):
    instance.product.flush_price_cache()
signals.post_save.connect(flush_price_cache, sender=ProductPrice)
signals.post_delete.connect(flush_price_cache, sender=ProductPrice)



