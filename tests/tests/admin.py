from django.contrib import admin

from tests.models import Product, Price


class PriceInline(admin.TabularInline):
    model = Price
    extra = 0


admin.site.register(Product,
    inlines=[PriceInline],
    )
