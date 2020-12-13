# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from plata.product.models import ProductBase
from plata.shop.models import PriceBase


class Product(ProductBase, PriceBase):
    """
    This product model is a price too, which means that only one price
    can exist. The administration interface is even simpler when following
    this approach.
    """

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

    def get_price(self, *args, **kwargs):
        return self

    def handle_order_item(self, orderitem):
        ProductBase.handle_order_item(self, orderitem)
        PriceBase.handle_order_item(self, orderitem)
