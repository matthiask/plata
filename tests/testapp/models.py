from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from plata.product.models import ProductBase
from plata.shop.models import PriceBase


@python_2_unicode_compatible
class Product(ProductBase):
    name = models.CharField(max_length=100)
    items_in_stock = models.IntegerField(default=0)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('plata_product_detail', (self.pk,), {})

    @property
    def sku(self):
        return u''


class Price(PriceBase):
    product = models.ForeignKey(Product, related_name='prices')

    class Meta:
        ordering = ['-id']
