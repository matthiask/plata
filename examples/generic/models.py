# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.utils.translation import ugettext as _
from django.conf import settings
from django.db import models
from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey
from django.contrib.contenttypes.models import ContentType

# from django.core.files.storage import FileSystemStorage
# from django.core.validators import validate_comma_separated_integer_list
from django.utils.encoding import python_2_unicode_compatible
from django.urls import reverse
from django.template.loader import render_to_string
from plata.product.models import ProductBase
from plata.shop.models import PriceBase
from plata.shipping.models import CountryGroup


CONTENT_MODELS = models.Q(app_label="generic", model="thing") | models.Q(
    app_label="generic", model="download"
)


@python_2_unicode_compatible
class Product(ProductBase):
    """flexible product that can address different content models"""

    code = models.SlugField(
        verbose_name=_("Code"),
        blank=False,
        max_length=63,
        help_text=_("Short unique code for this product."),
    )
    is_active = models.BooleanField(_("is active"), default=True)
    content_type = models.ForeignKey(
        ContentType,
        verbose_name=_("content type"),
        on_delete=models.CASCADE,
        limit_choices_to=CONTENT_MODELS,
    )
    object_id = models.PositiveIntegerField(_("object id"))
    content_object = GenericForeignKey("content_type", "object_id")
    content_object.short_description = _("object title")

    class Meta:
        verbose_name = _("product")
        verbose_name_plural = _("products")

    def __str__(self):
        if hasattr(self.content_object, "name"):
            return self.content_object.name
        if hasattr(self.content_object, "title"):
            return self.content_object.title
        return self.code

    __str__.short_description = _("name")

    def get_absolute_url(self):
        return reverse("plata_product_detail", kwargs={"object_id": self.pk})

    def name(self):
        return self.__str__()

    def description(self):
        return self.content_object.description


class ProductPrice(PriceBase):
    product = models.ForeignKey(
        Product, verbose_name=_("product"), related_name="prices"
    )
    country_group = models.ForeignKey(
        CountryGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("country group"),
        help_text=_("The price is valid for this country or group of countries."),
    )

    class Meta:
        get_latest_by = "id"
        ordering = ["-id"]
        verbose_name = _("price")
        verbose_name_plural = _("prices")


@python_2_unicode_compatible
class Thing(models.Model):
    """
    Physical Product
    """

    name = models.CharField(verbose_name=_("Title"), blank=False, max_length=127)
    description = models.TextField(verbose_name=_("Description"), blank=True)
    weight = models.FloatField(
        verbose_name=_("weight"), help_text=_("in kg"), blank=True
    )
    products = GenericRelation(Product)

    class Meta:
        verbose_name = _("thing")
        verbose_name_plural = _("things")

    def product(self):
        """
        There should be only one, thus just return the first one
        """
        return self.products.all()[0]

    def __str__(self):
        return self.name

    __str__.short_description = _("name")


@python_2_unicode_compatible
class Download(models.Model):
    """
    Virtual Product
    """

    name = models.CharField(verbose_name=_("Title"), blank=False, max_length=127)
    description = models.TextField(verbose_name=_("Description"), blank=True)
    dfile = models.FileField(upload_to="downloads/", verbose_name=_("file"))
    products = GenericRelation(Product)

    class Meta:
        verbose_name = _("download")
        verbose_name_plural = _("downloads")

    def product(self):
        """
        There should be only one, thus just return the first one
        """
        return self.products.all()[0]

    def __str__(self):
        return self.name

    __str__.short_description = _("name")
