from datetime import datetime

from django.db import models
from django.db.models import Sum, signals
from django.utils.translation import ugettext_lazy as _

from plata.product.models import Product


class ProducerManager(models.Manager):
    def active(self):
        return self.filter(is_active=True)


class Producer(models.Model):
    is_active = models.BooleanField(_('is active'), default=True)
    name = models.CharField(_('name'), max_length=100)
    slug = models.SlugField(_('slug'), unique=True)
    ordering = models.PositiveIntegerField(_('ordering'), default=0)
    description = models.TextField(_('description'), blank=True)

    class Meta:
        app_label = 'product'
        ordering = ['ordering', 'name']
        verbose_name = _('producer')
        verbose_name_plural = _('producers')

    def __unicode__(self):
        return self.name


Product.add_to_class('producer', models.ForeignKey(Producer, blank=True, null=True,
    related_name='products', verbose_name=_('producer')))
