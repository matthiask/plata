# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from generic.models import Product, ProductPrice, Thing, Download


class ProductInline(GenericTabularInline):
    model = Product
    extra = 0
    min_num = 1
    max_num = 1


class ProductPriceInline(admin.TabularInline):
    model = ProductPrice
    extra = 0
    min_num = 1


class ProductAdmin(admin.ModelAdmin):
    search_fields = ("code", "name")
    list_display = ("code", "is_active", "content_object")
    list_filter = ["content_type", "is_active"]
    list_editable = ("is_active",)
    ordering = ("code",)
    readonly_fields = ("content_object",)
    inlines = [ProductPriceInline]

    def has_add_permission(self, request):
        """
        Add products only via Thing/Download Inlines!
        """
        return False


admin.site.register(Product, ProductAdmin)


class ThingAdmin(admin.ModelAdmin):
    search_fields = ("name", "description")
    list_display = ("name", "weight")
    # list_filter = ['series', ]
    inlines = [ProductInline]


admin.site.register(Thing, ThingAdmin)


class DownloadAdmin(admin.ModelAdmin):
    search_fields = ("name", "description")
    list_display = ("name",)
    # list_filter = ['series', ]
    inlines = [ProductInline]


admin.site.register(Download, DownloadAdmin)
