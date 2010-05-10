from django import forms
from django.contrib import admin
from django.forms.util import ErrorList
from django.utils.translation import ugettext_lazy as _

from . import models


class ProductPriceInline(admin.TabularInline):
    model = models.ProductPrice

class ProductImageInline(admin.TabularInline):
    model = models.ProductImage


class ProductVariationForm(forms.ModelForm):
    def clean(self):
        options = self.cleaned_data.get('options', [])
        groups_on_product = set(self.instance.product.option_groups.values_list('id', flat=True))
        groups_on_variation = [o.group_id for o in options]
        options_errors = []

        if len(groups_on_variation) != len(set(groups_on_variation)):
            options_errors.append(_('Only one option per group allowed.'))
        if groups_on_product != set(groups_on_variation):
            options_errors.append(_('Please select an option from all groups.'))

        if options_errors:
            self._errors['options'] = ErrorList(options_errors)

        return self.cleaned_data


class ProductVariationInline(admin.TabularInline):
    model = models.ProductVariation
    form = ProductVariationForm

class OptionInline(admin.TabularInline):
    model = models.Option

admin.site.register(models.TaxClass,
    list_display=('name', 'rate', 'priority'),
    )

admin.site.register(models.Category,
    list_display=('is_active', 'is_internal', '__unicode__', 'ordering'),
    list_display_links=('__unicode__',),
    list_filter=('is_active', 'is_internal'),
    prepopulated_fields={'slug': ('name',)},
    )

admin.site.register(models.OptionGroup,
    inlines=[OptionInline],
    list_display=('name',),
    )

admin.site.register(models.Product,
    inlines=[ProductVariationInline, ProductPriceInline, ProductImageInline],
    list_display=('is_active', 'name', 'sku', 'ordering'),
    list_display_links=('name',),
    list_filter=('is_active',),
    prepopulated_fields={'slug': ('name',)},
    )

admin.site.register(models.Discount,
    list_display=('name', 'type', 'code', 'value'),
    list_filter=('type',),
    )
