from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from . import models


class ProductAdmin(admin.ModelAdmin):
    list_display = ("is_active", "name", "ordering", "unit_price")
    list_display_links = ("name",)
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "description")


admin.site.register(models.Product, ProductAdmin)
