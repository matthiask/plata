"""
This module contains the original product model of Plata
"""

from django.db import models
from django.db.models import Count, signals
from django.utils.translation import ugettext_lazy as _

import plata
from plata.compat import product as itertools_product
from plata.shop.models import Price, PriceManager


class ProductPrice(Price):
    product = models.ForeignKey('product.Product', verbose_name=_('product'),
        related_name='prices')

    class Meta:
        app_label = 'product'
        get_latest_by = 'id'
        ordering = ['-valid_from']
        verbose_name = _('price')
        verbose_name_plural = _('prices')

    objects = PriceManager()


class CategoryManager(models.Manager):
    def active(self):
        return self.filter(is_active=True)

    def public(self):
        return self.filter(is_active=True, is_internal=False)


class Category(models.Model):
    """
    Categories are both used for external and internal organization of products.
    If the ``is_internal`` flag is set, categories will never appear in the shop
    but can be used f.e. to group discountable products together.
    """

    is_active = models.BooleanField(_('is active'), default=True)
    is_internal = models.BooleanField(_('is internal'), default=False,
        help_text=_('Only used to internally organize products, f.e. for discounting.'))

    name = models.CharField(_('name'), max_length=100)
    slug = models.SlugField(_('slug'), unique=True)
    ordering = models.PositiveIntegerField(_('ordering'), default=0)
    description = models.TextField(_('description'), blank=True)

    parent = models.ForeignKey('self', blank=True, null=True,
        limit_choices_to={'parent__isnull': True},
        related_name='children', verbose_name=_('parent'))

    class Meta:
        app_label = 'product'
        ordering = ['parent__ordering', 'parent__name', 'ordering', 'name']
        verbose_name = _('category')
        verbose_name_plural = _('categories')

    objects = CategoryManager()

    def __unicode__(self):
        if self.parent_id:
            return u'%s - %s' % (self.parent, self.name)
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('plata_category_detail', (), {'object_id': self.pk})


class OptionGroup(models.Model):
    """
    Option group, f.e. size or color

    TODO What about user visible vs machine readable names?
    """

    name = models.CharField(_('name'), max_length=100)

    class Meta:
        app_label = 'product'
        ordering = ['id']
        verbose_name = _('option group')
        verbose_name_plural = _('option groups')

    def __unicode__(self):
        return self.name


class Option(models.Model):
    """
    Single option belonging to an option group, f.e. red, blue or yellow for color
    or XL, L or M for sizes
    """

    group = models.ForeignKey(OptionGroup, related_name='options',
        verbose_name=_('option group'))
    name = models.CharField(_('name'), max_length=100)
    value = models.CharField(_('value'), max_length=100)
    ordering = models.PositiveIntegerField(_('ordering'), default=0)

    class Meta:
        app_label = 'product'
        ordering = ['group', 'ordering']
        verbose_name = _('option')
        verbose_name_plural = _('options')

    def __unicode__(self):
        return self.name

    def full_name(self):
        return u'%s - %s' % (self.group, self.name)


class ProductManager(models.Manager):
    # TODO which of these methods are guaranteed to exist / required?
    def active(self):
        return self.filter(is_active=True)

    def featured(self):
        return self.active().filter(is_featured=True)

    def bestsellers(self, queryset=None):
        queryset = queryset or self
        return queryset.annotate(sold=Count('variations__orderitem')).order_by('-sold')

    def also_bought(self, product):
        return self.bestsellers(
            self.exclude(id=product.id).exclude(variations__orderitem__isnull=True
                ).filter(variations__orderitem__order__items__product__product=product))


if False: # TODO?
    from feincms.models import Base
else:
    Base = models.Model

class Product(Base):
    """
    Default product model

    Knows how to determine its own price and the stock of all its variations.
    """

    is_active = models.BooleanField(_('is active'), default=True)
    is_featured = models.BooleanField(_('is featured'), default=False)
    name = models.CharField(_('name'), max_length=100)
    slug = models.SlugField(_('slug'), unique=True)
    ordering = models.PositiveIntegerField(_('ordering'), default=0)
    sku = models.CharField(_('SKU'), max_length=100, unique=True)

    categories = models.ManyToManyField(Category,
        verbose_name=_('categories'), related_name='products',
        blank=True, null=True)
    description = models.TextField(_('description'), blank=True)
    option_groups = models.ManyToManyField(OptionGroup, related_name='products',
        blank=True, null=True, verbose_name=_('option groups'))

    class Meta:
        app_label = 'product'
        ordering = ['ordering', 'name']
        verbose_name = _('product')
        verbose_name_plural = _('products')

    objects = ProductManager()

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = self.slug
        super(Product, self).save(*args, **kwargs)
        self.flush_price_cache()

    @models.permalink
    def get_absolute_url(self):
        return ('plata_product_detail', (), {'object_id': self.pk})

    @property
    def main_image(self):
        if not hasattr(self, '_main_image'):
            try:
                self._main_image = self.images.all()[0]
            except IndexError:
                self._main_image = None
        return self._main_image

    def get_price(self, currency=None):
        return self.prices.determine_price(self, currency)

    def get_prices(self):
        return self.prices.determine_prices(self)

    def flush_price_cache(self):
        self.prices.flush_price_cache(self)

    def in_sale(self, currency):
        prices = dict(self.get_prices())
        if currency in prices and prices[currency]['sale']:
            return True
        return False

    def create_variations(self):
        variations = itertools_product(*[group.options.all() for group in self.option_groups.all()])

        for idx, variation in enumerate(variations):
            try:
                qset = self.variations
                for o in variation:
                    qset = qset.filter(options=o)

                instance = qset.get()
            except ProductVariation.DoesNotExist:
                parts = [self.sku]
                parts.extend(o.value for o in variation)
                instance = self.variations.create(
                    is_active=self.is_active,
                    sku=u'-'.join(parts),
                    )
                instance.options = variation

            instance.ordering = idx
            instance.save()

    def items_in_stock(self):
        items = {}

        for variation in self.variations.all():
            key = '_'.join(str(pk) for pk in variation.options.values_list('pk', flat=True))
            items[key] = variation.items_in_stock

        return items


class ProductVariation(models.Model):
    """
    This is the physical product, sporting a field for the stock amount etc.
    """

    product = models.ForeignKey(Product, related_name='variations')
    is_active = models.BooleanField(_('is active'), default=True)
    sku = models.CharField(_('SKU'), max_length=100, unique=True)
    items_in_stock = models.IntegerField(_('items in stock'), default=0)
    options = models.ManyToManyField(Option, related_name='variations',
        blank=True, null=True, verbose_name=_('options'))
    options_name_cache = models.CharField(_('options name cache'), max_length=100,
        blank=True, editable=False)
    ordering = models.PositiveIntegerField(_('ordering'), default=0)

    class Meta:
        app_label = 'product'
        ordering = ['ordering', 'product']
        verbose_name = _('product variation')
        verbose_name_plural = _('product variations')

    def __unicode__(self):
        if self.options_name_cache:
            return u'%s (%s)' % (self.product, self.options_name_cache)
        return u'%s' % self.product

    def _regenerate_cache(self, options=None):
        if options is None:
            options = self.options.all()

        self.options_name_cache = u', '.join(unicode(o) for o in options)

    def can_delete(self):
        return self.orderitem_set.count() == 0

    def _generate_proxy(method):
        def func(self, *args, **kwargs):
            return getattr(self.product, method)(*args, **kwargs)
        return func

    get_absolute_url = _generate_proxy('get_absolute_url')
    get_price = _generate_proxy('get_price')


def flush_price_cache(instance, **kwargs):
    instance.product.flush_price_cache()
signals.post_save.connect(flush_price_cache, sender=ProductPrice)
signals.post_delete.connect(flush_price_cache, sender=ProductPrice)


class ProductImage(models.Model):
    product = models.ForeignKey(Product, verbose_name=_('product'),
        related_name='images')
    image = models.ImageField(_('image'),
        upload_to=lambda instance, filename: 'products/%s/%s' % (instance.product.slug, filename))
    ordering = models.PositiveIntegerField(_('ordering'), default=0)

    class Meta:
        app_label = 'product'
        ordering = ['ordering']
        verbose_name = _('product image')
        verbose_name_plural = _('product images')

    def __unicode__(self):
        return self.image.name
