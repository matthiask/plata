from django.contrib import admin

from plata.shipping.models import Country, CountryGroup, Postage, ShippingProvider


@admin.register(CountryGroup)
class CountryGroupAdmin(admin.ModelAdmin):
    # search_fields = ('name', 'code')
    list_display = ("id", "name", "code")
    list_editable = ("name", "code")
    ordering = ("code",)
    prepopulated_fields = {"code": ("name",)}


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    search_fields = ("country", "country_group__name")
    list_display = ("id", "country", "country_group")
    list_filter = ["country_group"]
    list_editable = ("country", "country_group")
    ordering = ("country_group", "country")


@admin.register(ShippingProvider)
class ShippingProviderAdmin(admin.ModelAdmin):
    search_fields = ("name", "country_group", "remarks")
    list_display = ("id", "name")
    list_filter = ["country_group"]
    list_editable = ("name",)
    ordering = ("name",)


@admin.register(Postage)
class PostageAdmin(admin.ModelAdmin):
    search_fields = ("name", "provider__name")
    list_display = (
        "__str__",
        "max_size_f",
        "max_weight_f",
        "price_internal",
        "currency",
        "country_group",
    )
    list_filter = ["provider", "country_group", "currency", "price_includes_tax"]
    list_editable = ("price_internal",)  # because that tends to change yearly
    ordering = ("provider", "country_group")
