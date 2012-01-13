"""
Product model base implementation -- you do not need to use this

It may save you some typing though.
"""

from django.core.cache import cache
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
        if currency is None:
            currency = (orderitem.currency if orderitem else
                plata.shop_instance().default_currency())

        prices = dict(self.get_prices()).get(currency, {})

        if prices.get('sale'):
            return prices['sale']

        if prices.get('normal'):
            return prices['normal']
        elif prices.get('sale'):
            return prices['sale']

        raise self.DoesNotExist

    def get_prices(self):
        key = 'product-prices-%s' % self.pk

        if cache.has_key(key):
            return cache.get(key)

        _prices = {}
        for price in self.prices.active().order_by('valid_from'):
            # First item is normal price, second is sale price
            _prices.setdefault(price.currency, [None, None])[int(price.is_sale)] = price

        prices = []
        for currency in plata.settings.CURRENCIES:
            p = _prices.get(currency)
            if not p:
                continue

            # Sale prices are only active if they are newer than the newest
            # normal price
            if (p[0] and p[1]) and p[0].valid_from > p[1].valid_from:
                p[1] = None

            prices.append((currency, {
                'normal': p[0],
                'sale': p[1],
                }))

        cache.set(key, prices)
        return prices

    def flush_price_cache(self):
        key = 'product-prices-%s' % self.pk
        cache.delete(key)

    def handle_order_item(self, orderitem):
        orderitem.name = unicode(self)
        orderitem.sku = getattr(self, 'sku', u'')


def flush_price_cache(instance, **kwargs):
    instance.product.flush_price_cache()


def register_price_cache_handlers(ProductPrice):
    signals.post_save.connect(flush_price_cache, sender=ProductPrice)
    signals.post_delete.connect(flush_price_cache, sender=ProductPrice)
