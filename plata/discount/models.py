from datetime import date, datetime

from django import forms
from django.core.urlresolvers import get_callable
from django.db import models
from django.utils.translation import ugettext_lazy as _

from plata.fields import CurrencyField
from plata.product.models import Category, Product
from plata.utils import JSONFieldDescriptor


class DiscountBase(models.Model):
    AMOUNT_EXCL_TAX = 10
    AMOUNT_INCL_TAX = 20
    PERCENTAGE = 30

    TYPE_CHOICES = (
        (AMOUNT_EXCL_TAX, _('amount excl. tax')),
        (AMOUNT_INCL_TAX, _('amount incl. tax')),
        (PERCENTAGE, _('percentage')),
        )

    CONFIG_OPTIONS = [
        ('all', {
            'title': _('All products'),
            }),
        ('exclude_sale', {
            'title': _('Exclude sale prices'),
            'form_fields': [
                ('exclude_sales', forms.BooleanField(label=_('exclude sales'), required=False, initial=True)),
                ],
            'query': lambda item: Q(price__sale=False),
            }),
        ('only_categories', {
            'title': _('Only product from selected categories'),
            'form_fields': [
                ('categories', forms.ModelMultipleChoiceField(
                    Category.objects.all(),
                    label=_('only from categories'),
                    required=True)),
                ],
            'query': lambda value: Q(category__in=value),
            }),
        ('products', {
            'title': _('Discountable products list'),
            'form_fields': [
                ('products', forms.ModelMultipleChoiceField(
                    Product.objects.all(),
                    label=_('products'),
                    required=True)),
                ],
            'query': lambda value: Q(category__in=value),
            }),
        ]

    name = models.CharField(_('name'), max_length=100)

    type = models.PositiveIntegerField(_('type'), choices=TYPE_CHOICES)
    value = models.DecimalField(_('value'), max_digits=10, decimal_places=2)

    config_json = models.TextField(_('configuration'), blank=True)
    config = JSONFieldDescriptor('config_json')

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.name

    def eligible_products(self, queryset=None):
        if not queryset:
            queryset = plata.shop_instance().product_model._default_manager.all()

        data = self.data_json
        if 'eligible_filter' in data:
            queryset = queryset.filter(**dict((str(k), v) for k, v in data['eligible_filter'].items()))

        return queryset

    def apply(self, order, items, **kwargs):
        if not items:
            return

        if self.type == self.AMOUNT_EXCL_TAX:
            self.apply_amount_discount(order, items, tax_included=False)
        elif self.type == self.AMOUNT_INCL_TAX:
            self.apply_amount_discount(order, items, tax_included=True)
        elif self.type == self.PERCENTAGE:
            self.apply_percentage_discount(order, items)
        else:
            raise NotImplementedError, 'Unknown discount type %s' % self.type

    def apply_amount_discount(self, order, items, tax_included):
        eligible_products = self.eligible_products().values_list('id', flat=True)

        eligible_items = [item for item in items if item.variation.product_id in eligible_products]

        if tax_included:
            # TODO how should this value be calculated in the presence of multiple tax rates?
            tax_rate = items[0].get_product_price().tax_class.rate
            discount = self.value / (1 + tax_rate/100)
        else:
            discount = self.value

        items_subtotal = sum([item.discounted_subtotal_excl_tax for item in eligible_items], 0)

        if items_subtotal < discount:
            remaining = discount - items_subtotal
            discount = items_subtotal

        for item in eligible_items:
            item._line_item_discount += item.discounted_subtotal_excl_tax / items_subtotal * discount

    def apply_percentage_discount(self, order, items):
        eligible_products = self.eligible_products().values_list('id', flat=True)

        factor = self.value / 100

        for item in items:
            if item.variation.product_id not in eligible_products:
                continue

            item._line_item_discount += item.discounted_subtotal_excl_tax * factor


class Discount(DiscountBase):
    code = models.CharField(_('code'), max_length=30, unique=True)

    is_active = models.BooleanField(_('is active'), default=True)
    valid_from = models.DateField(_('valid from'), default=date.today)
    valid_until = models.DateField(_('valid until'), blank=True, null=True)

    allowed_uses = models.IntegerField(_('number of allowed uses'),
        blank=True, null=True,
        help_text=_('Leave empty if there is no limit on the number of uses of this discount.'))
    used = models.IntegerField(_('number of times already used'), default=0)

    class Meta:
        verbose_name = _('discount')
        verbose_name_plural = _('discounts')

    def validate(self, order):
        messages = []
        if not self.is_active:
            messages.append(_('Discount is inactive.'))

        today = date.today()
        if today < self.valid_from:
            messages.append(_('Discount is not active yet.'))
        if self.valid_until and today > self.valid_until:
            messages.append(_('Discount is expired.'))

        if messages:
            raise ValidationError(messages)

        return True
