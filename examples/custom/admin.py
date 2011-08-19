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

admin.site.register(models.Contact,
    list_display=('user', 'zip_code', 'city', 'country'),
    )
