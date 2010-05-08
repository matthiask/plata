from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from . import models


class ProductPriceInline(admin.TabularInline):
    model = models.ProductPrice

class ProductImageInline(admin.TabularInline):
    model = models.ProductImage

class ProductVariationInline(admin.TabularInline):
    model = models.ProductVariation

class OptionInline(admin.TabularInline):
    model = models.Option

admin.site.register(models.TaxClass,
    list_display=('name', 'rate', 'priority'),
    )

admin.site.register(models.Category,
    list_display=('is_active', 'is_internal', '__unicode__', 'ordering'),
    list_display_links=('__unicode__',),
    list_filter=('is_active', 'is_internal'),
    prepopulated_fields={'slug': ('name',)},
    )

admin.site.register(models.OptionGroup,
    inlines=[OptionInline],
    list_display=('name',),
    )

admin.site.register(models.Product,
    inlines=[ProductVariationInline, ProductPriceInline, ProductImageInline],
    list_display=('is_active', 'name', 'sku', 'ordering'),
    list_display_links=('name',),
    list_filter=('is_active',),
    prepopulated_fields={'slug': ('name',)},
    )

admin.site.register(models.Discount,
    list_display=('name', 'type', 'code', 'value'),
    list_filter=('type',),
    )
