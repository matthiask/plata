from datetime import datetime

from django.db import models
from django.db.models import Sum, signals
from django.utils.translation import ugettext_lazy as _

# TODO do not hardcode imports
from plata.product.models import Product
from plata.shop.models import Order


class OptionGroup(models.Model):
    name = models.CharField(_('name'), max_length=100)


class Option(models.Model):
    group = models.ForeignKey(OptionGroup, related_name='options',
        verbose_name=_('option group'))
    name = models.CharField(_('name'), max_length=100)
    value = models.CharField(_('value'), max_length=100)
    ordering = models.PositiveIntegerField(_('ordering'), default=0)


class ProductGroup(models.Model):
    option_groups = models.ManyToManyField(OptionGroup,
        verbose_name=_('option groups'))
    primary_product = models.ForeignKey(Product, related_name='primary_product_groups',
        verbose_name=_('primary product'))


Product.add_to_class('product_group', models.ForeignKey(ProductGroup,
    blank=True, null=True, related_name='product_variations',
    verbose_name=_('product group')))
