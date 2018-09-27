from django.contrib import admin

from testapp.models import Price, Product


class PriceInline(admin.TabularInline):
    model = Price
    extra = 0


admin.site.register(Product, inlines=[PriceInline])
