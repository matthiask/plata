# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from django.contrib import admin
from plata.shipping.models import Country, CountryGroup, ShippingProvider, Postage


class CountryGroupAdmin(admin.ModelAdmin):
    # search_fields = ('name', 'code')
    list_display = ('id', 'name', 'code')
    list_editable = ('name', 'code')
    ordering = ('code',)
    prepopulated_fields = {'code': ('name',)}


class CountryAdmin(admin.ModelAdmin):
    search_fields = ('country', 'country_group__name')
    list_display = ('id', 'country', 'country_group')
    list_filter = ['country_group']
    list_editable = ('country', 'country_group',)
    ordering = ('country_group', 'country')


class ShippingProviderAdmin(admin.ModelAdmin):
    search_fields = ('name', 'country_group', 'remarks')
    list_display = ('id', 'name',)
    list_filter = ['country_group']
    list_editable = ('name',)
    ordering = ('name',)


class PostageAdmin(admin.ModelAdmin):
    search_fields = ('name', 'provider__name')
    list_display = ('__str__', 'max_size_f', 'max_weight_f', 'price_internal', 'currency', 'country_group')
    list_filter = ['provider', 'country_group', 'currency', 'price_includes_tax']
    list_editable = ('price_internal',)  # because that tends to change yearly
    ordering = ('provider', 'country_group', )


admin.site.register(CountryGroup, CountryGroupAdmin)
admin.site.register(Country, CountryAdmin)
admin.site.register(ShippingProvider, ShippingProviderAdmin)
admin.site.register(Postage, PostageAdmin)
