from django import forms
from django.contrib import admin
from django.forms.models import BaseInlineFormSet
from django.utils.translation import ugettext_lazy as _

from . import models


class ProductPriceInline(admin.TabularInline):
    model = models.ProductPrice
    extra = 0

class ProductImageInline(admin.TabularInline):
    model = models.ProductImage
    extra = 0


class ProductVariationFormSet(BaseInlineFormSet):
    def clean(self):
        super(ProductVariationFormSet, self).clean()

        variations = set()
        skus = set()

        for form in self.forms:
            if self.can_delete and self._should_delete_form(form) or \
                    (not form.instance.pk and not form.has_changed()) or \
                    (not form.is_valid()):
                # Skip forms which will not end up as instances or aren't valid yet
                continue

            options = form.cleaned_data.get('options')

            if options:
                s = tuple(sorted(o.id for o in options))

                if s in variations:
                    form._errors['options'] = form.error_class([
                        _('Combination of options already encountered.')])
                    continue

                variations.add(s)

            sku = form.cleaned_data.get('sku')
            if not sku or sku in skus:
                # Need to regenerate SKU
                parts = [self.instance.sku]
                parts.extend(o.value for o in options)
                sku = u'-'.join(parts)

                while sku in skus:
                    sku += u'-'

                form.instance.sku = sku
            skus.add(form.instance.sku)

    def save(self):
        super(ProductVariationFormSet, self).save()
        self.instance.create_variations()


class ProductVariationForm(forms.ModelForm):
    sku = forms.CharField(label=_('SKU'), max_length=100, required=False)

    def clean(self):
        options = self.cleaned_data.get('options', [])
        groups_on_product_objects = self.instance.product.option_groups.all()
        groups_on_product = set(g.id for g in groups_on_product_objects)
        groups_on_variation = [o.group_id for o in options]
        options_errors = []

        if len(groups_on_variation) != len(set(groups_on_variation)):
            options_errors.append(_('Only one option per group allowed.'))
        if groups_on_product != set(groups_on_variation):
            options_errors.append(_('Please select options from the following groups: %s') %\
                u', '.join(unicode(g) for g in groups_on_product_objects))

        if options_errors:
            self._errors['options'] = self.error_class(options_errors)

        return self.cleaned_data


class ProductVariationInline(admin.TabularInline):
    model = models.ProductVariation
    form = ProductVariationForm
    formset = ProductVariationFormSet
    extra = 0
    can_delete = False

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
    search_fields=('name', 'description'),
    )

admin.site.register(models.OptionGroup,
    inlines=[OptionInline],
    list_display=('name',),
    )

admin.site.register(models.Product,
    filter_horizontal=('categories',),
    inlines=[ProductVariationInline, ProductPriceInline, ProductImageInline],
    list_display=('is_active', 'name', 'sku', 'ordering'),
    list_display_links=('name',),
    list_filter=('is_active',),
    prepopulated_fields={'slug': ('name',), 'sku': ('name',)},
    search_fields=('name', 'description'),
    )

# All fields are read only; this model is only used for raw_id_fields supports
admin.site.register(models.ProductVariation,
    list_display=('product', 'is_active', 'sku', 'items_in_stock', 'ordering'),
    list_filter=('is_active',),
    readonly_fields=('product', 'is_active', 'sku', 'items_in_stock', 'options', 'ordering'),
    search_fields=('product__name', 'product__description'),
    )

admin.site.register(models.Discount,
    list_display=('name', 'type', 'code', 'value'),
    list_filter=('type',),
    )
