from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from . import models


class ProductPriceInline(admin.TabularInline):
    model = models.ProductPrice

class ProductImageInline(admin.TabularInline):
    model = models.ProductImage


admin.site.register(models.TaxClass,
    list_display=('name', 'rate', 'priority'),
    )

admin.site.register(models.Product,
    inlines=[ProductPriceInline, ProductImageInline],
    list_display=('name', 'description'),
    )

admin.site.register(models.Discount,
    list_display=('name', 'type', 'code', 'value'),
    list_filter=('type',),
    )
