from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from feincms.admin.item_editor import ItemEditor, FEINCMS_CONTENT_FIELDSET

from plata.product.admin import ProductAdmin, ProductVariationInline,\
    ProductPriceInline, ProductImageInline, ProductForm
from plata.product.models import Product
from . import models


class CMSProductForm(ProductForm):
    class Meta:
        model = models.CMSProduct


class ProductAdmin(ProductAdmin, ItemEditor):
    fieldsets = [(None, {
        'fields': ('is_active', 'name', 'slug', 'sku', 'is_featured'),
        }),
        FEINCMS_CONTENT_FIELDSET,
        (_('Properties'), {
            'fields': ('ordering', 'description', 'producer', 'categories',
                'option_groups', 'create_variations'),
        }),
        ]
    form = CMSProductForm
    inlines = [ProductVariationInline, ProductPriceInline, ProductImageInline]


admin.site.unregister(Product)
admin.site.register(models.CMSProduct, ProductAdmin)
