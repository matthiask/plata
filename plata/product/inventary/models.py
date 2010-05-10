from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from plata.compat import product as itertools_product
from plata.product import abstract


__all__ = ['Product', 'ProductPrice', 'ProductImage',
    'Category', 'Discount', 'TaxClass', 'ProductVariation']


class TaxClass(abstract.TaxClass):
    class Meta:
        app_label = 'product'
        ordering = ['-priority']
        verbose_name = _('tax class')
        verbose_name_plural = _('tax classes')


class Category(abstract.Category):
    class Meta:
        app_label = 'product'
        ordering = ['ordering', 'name']
        verbose_name = _('category')
        verbose_name_plural = _('categories')


class OptionGroup(models.Model):
    name = models.CharField(_('name'), max_length=100)

    class Meta:
        app_label = 'product'
        verbose_name = _('option group')
        verbose_name_plural = _('option groups')

    def __unicode__(self):
        return self.name


class Option(models.Model):
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


class Product(abstract.Product):
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

    @property
    def main_image(self):
        try:
            return self.images.all()[0]
        except IndexError:
            return None

    def create_variations(self):
        variations = itertools_product(*[group.options.all() for group in self.option_groups.all()])

        for idx, variation in enumerate(variations):
            try:
                qset = self.variations
                for o in variation:
                    qset = qset.filter(options=o)

                instance = qset.get()
            except ProductVariation.DoesNotExist:
                instance = self.variations.create(
                    is_active=self.is_active,
                    sku=self.sku + '-' + u'-'.join(v.value for v in variation),
                    )
                instance.options = variation
            except ProductVariation.MultipleObjectsReturned:
                raise Exception('DAMN!')

            instance.ordering = idx
            instance.save()


class ProductVariation(models.Model):
    product = models.ForeignKey(Product, related_name='variations')
    is_active = models.BooleanField(_('is active'), default=True)
    sku = models.CharField(_('SKU'), max_length=100, blank=True)
    items_in_stock = models.IntegerField(_('items in stock'), default=0)
    options = models.ManyToManyField(Option, related_name='products',
        blank=True, null=True, verbose_name=_('options'))
    ordering = models.PositiveIntegerField(_('ordering'), default=0)

    class Meta:
        app_label = 'product'
        ordering = ['ordering']
        verbose_name = _('product variation')
        verbose_name_plural = _('product variations')

    def __unicode__(self):
        options = u', '.join(unicode(o) for o in self.options.all())

        if options:
            return u'%s (%s)' % (self.product, options)

        return u'%s' % self.product


class ProductPrice(abstract.ProductPrice):
    product = models.ForeignKey(Product, verbose_name=_('product'),
        related_name='prices')
    tax_class = models.ForeignKey(TaxClass, verbose_name=_('tax class'))

    class Meta:
        app_label = 'product'
        get_latest_by = 'id'
        ordering = ['-valid_from']
        verbose_name = _('product price')
        verbose_name_plural = _('product prices')


class ProductImage(models.Model):
    product = models.ForeignKey(Product, verbose_name=_('product'),
        related_name='images')
    image = models.ImageField(_('image'),
        upload_to=lambda instance, filename: '%s/%s' % (instance.product.slug, filename))
    ordering = models.PositiveIntegerField(_('ordering'), default=0)

    class Meta:
        app_label = 'product'
        ordering = ['ordering']
        verbose_name = _('product image')
        verbose_name_plural = _('product images')

    def __unicode__(self):
        return self.image.name


class Discount(abstract.DiscountBase):
    code = models.CharField(_('code'), max_length=30, unique=True)

    is_active = models.BooleanField(_('is active'), default=True)
    valid_from = models.DateField(_('valid from'), default=date.today)
    valid_until = models.DateField(_('valid until'), blank=True, null=True)

    class Meta:
        app_label = 'product'
        verbose_name = _('discount')
        verbose_name_plural = _('discounts')

    def validate(self, order):
        messages = []
        if not self.is_active:
            messages.append(_('Discount is inactive.'))

        today = date.today()
        if today < self.valid_from:
            messages.append(_('Discount is not active yet.'))
        if self.valid_until and today > self.valid_until:
            messages.append(_('Discount is expired.'))

        if messages:
            raise ValidationError(messages)

        return True
