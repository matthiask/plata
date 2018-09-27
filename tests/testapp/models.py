from django.db import models
from django.utils.encoding import python_2_unicode_compatible

try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse

from plata.product.models import ProductBase
from plata.shop.models import PriceBase


@python_2_unicode_compatible
class Product(ProductBase):
    name = models.CharField(max_length=100)
    items_in_stock = models.IntegerField(default=0)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("plata_product_detail", args=(self.pk,))

    @property
    def sku(self):
        return u""


class Price(PriceBase):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="prices"
    )

    class Meta:
        ordering = ["-id"]
