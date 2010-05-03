from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from feincms.admin.item_editor import ItemEditor

from . import models


class ProductPriceInline(admin.TabularInline):
    model = models.ProductPrice


class ProductAdmin(ItemEditor):
    show_on_top = ('is_active', 'name', 'slug')
    inlines=[ProductPriceInline]
    list_display=('is_active', 'name', 'sku', 'items_in_stock', 'ordering')
    list_display_links=('name',)
    list_filter=('is_active',)
    prepopulated_fields={'slug': ('name',)}


admin.site.register(models.TaxClass,
    list_display=('name', 'rate', 'priority'),
    )

admin.site.register(models.Category,
    list_display=('is_active', 'is_internal', '__unicode__', 'ordering'),
    list_display_links=('__unicode__',),
    list_filter=('is_active', 'is_internal'),
    prepopulated_fields={'slug': ('name',)},
    )

admin.site.register(models.Product, ProductAdmin)

admin.site.register(models.Discount,
    list_display=('name', 'type', 'code', 'value'),
    list_filter=('type',),
    )
