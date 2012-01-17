from django.db import models

from plata.product.models import ProductBase
from plata.shop.models import PriceBase


class Product(ProductBase):
    name = models.CharField(max_length=100)
    items_in_stock = models.IntegerField(default=0)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


class Price(PriceBase):
    product = models.ForeignKey(Product, related_name='prices')

    class Meta:
        ordering = ['-id']
