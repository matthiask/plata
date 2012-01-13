"""
Product model base implementation -- you do not need to use this

It may save you some typing though.
"""

from django.db import models
from django.db.models import signals


class ProductBase(models.Model):
    """(Nearly) the simplest product model ever"""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        super(ProductBase, self).save(*args, **kwargs)
        self.flush_price_cache()

    def get_price(self, currency=None, orderitem=None):
        return self.prices.determine_price(self, currency)

    def get_prices(self):
        return self.prices.determine_prices(self)

    def flush_price_cache(self):
        self.prices.flush_price_cache(self)

    def handle_order_item(self, orderitem):
        orderitem.name = unicode(self)
        orderitem.sku = getattr(self, 'sku', u'')

def flush_price_cache(instance, **kwargs):
    instance.product.flush_price_cache()


def register_price_cache_handlers(ProductPrice):
    signals.post_save.connect(flush_price_cache, sender=ProductPrice)
    signals.post_delete.connect(flush_price_cache, sender=ProductPrice)
