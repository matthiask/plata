from datetime import datetime

from django.db import models
from django.utils.translation import ugettext_lazy as _


class TaxClass(models.Model):
    name = models.CharField(_('name'), max_length=100)
    rate = models.DecimalField(_('rate'), max_digits=10, decimal_places=2)
    priority = models.PositiveIntegerField(_('priority'), default=0,
        help_text = _('Used to order the tax classes in the administration interface.'))

    class Meta:
        ordering = ['-priority']
        verbose_name = _('tax class')
        verbose_name_plural = _('tax classes')


class Product(models.Model):
    name = models.CharField(_('name'), max_length=100)
    description = models.TextField(_('description'), blank=True)
    tax_included = models.BooleanField(_('tax included'), default=True,
        help_text=_('Unit price includes tax?'))

    class Meta:
        pass

    def __unicode__(self):
        return self.name

    @property
    def unit_price(self):
        return self.prices.latest().price


class ProductPrice(models.Model):
    product = models.ForeignKey(Product, verbose_name=_('product'),
        related_name='prices')
    created = models.DateTimeField(_('created'), default=datetime.now)
    unit_price = models.DecimalField(_('unit price'), max_digits=18, decimal_places=10)
    currency = models.CharField(_('currency'), max_length=10)

    class Meta:
        get_latest_by = 'created'
        ordering = ['-created']
        verbose_name = _('product price')
        verbose_name_plural = _('product prices')


class ProductImage(models.Model):
    product = models.ForeignKey(Product, verbose_name=_('product'),
        related_name='images')
    image = models.ImageField(_('image'),
        upload_to=lambda instance, filename: '%s/%s' % (instance.product.slug, filename))
    ordering = models.PositiveIntegerField(_('ordering'), default=0)

    class Meta:
        ordering = ['ordering']
        verbose_name = _('product image')
        verbose_name_plural = _('product images')

