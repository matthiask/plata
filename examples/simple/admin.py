from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from . import models


class ProductPriceInline(admin.TabularInline):
    model = models.ProductPrice
    extra = 0


class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductPriceInline]
    list_display = ('is_active', 'name', 'ordering')
    list_display_links = ('name',)
    list_filter = ('is_active',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')

admin.site.register(models.Product, ProductAdmin)


class ReadonlyModelAdmin(admin.ModelAdmin):
    actions = None # no "delete selected objects" action
    def has_delete_permission(self, request, obj=None):
        return False

# All fields are read only; these models are only used for raw_id_fields support
admin.site.register(models.ProductPrice,
    admin_class=ReadonlyModelAdmin,
    list_display=('__unicode__', 'product', 'currency', '_unit_price', 'tax_included',
        'tax_class', 'is_active', 'valid_from', 'valid_until', 'is_sale'),
    list_filter=('is_active', 'is_sale', 'tax_included', 'tax_class', 'currency'),
    readonly_fields=('product', 'currency', '_unit_price', 'tax_included', 'tax_class',
        'is_active', 'valid_from', 'valid_until', 'is_sale'),
    search_fields=('product__name', 'product__description', '_unit_price'),
    can_delete=False,
    )
