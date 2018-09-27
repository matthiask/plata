# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible

from plata.product.models import ProductBase
from plata.shop.models import PriceBase


@python_2_unicode_compatible
class Product(ProductBase):
    """(Nearly) the simplest product model ever"""

    is_active = models.BooleanField(_("is active"), default=True)
    name = models.CharField(_("name"), max_length=100)
    slug = models.SlugField(_("slug"), unique=True)
    ordering = models.PositiveIntegerField(_("ordering"), default=0)

    description = models.TextField(_("description"), blank=True)

    class Meta:
        ordering = ["ordering", "name"]
        verbose_name = _("product")
        verbose_name_plural = _("products")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("plata_product_detail", kwargs={"object_id": self.pk})


class ProductPrice(PriceBase):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name=_("product"),
        related_name="prices",
    )

    class Meta:
        get_latest_by = "id"
        ordering = ["-id"]
        verbose_name = _("price")
        verbose_name_plural = _("prices")
