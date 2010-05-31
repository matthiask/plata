from datetime import date, datetime

from django import forms
from django.core.exceptions import ValidationError
from django.core.urlresolvers import get_callable
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

import plata
from plata.fields import CurrencyField
from plata.product.models import Category, Product, ProductVariation
from plata.shop.processors import ProcessorBase
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
            'orderitem_query': lambda **values: Q(is_sale=False),
            }),
        ('products', {
            'title': _('Explicitly define discountable products'),
            'form_fields': [
                ('products', forms.ModelMultipleChoiceField(
                    Product.objects.all(),
                    label=_('products'),
                    required=True)),
                ],
            'variation_query': lambda products: Q(product__in=products),
            }),
        ('only_categories', {
            'title': _('Only products from selected categories'),
            'form_fields': [
                ('categories', forms.ModelMultipleChoiceField(
                    Category.objects.all(),
                    label=_('categories'),
                    required=True)),
                ],
            'variation_query': lambda categories: Q(product__categories__in=categories),
            }),
        ]

    name = models.CharField(_('name'), max_length=100)

    # TODO currency handling. Maybe split type/value into amount, tax, currency, percentage?
    type = models.PositiveIntegerField(_('type'), choices=TYPE_CHOICES)
    value = models.DecimalField(_('value'), max_digits=10, decimal_places=2)

    config_json = models.TextField(_('configuration'), blank=True)
    config = JSONFieldDescriptor('config_json')

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.name

    def eligible_products(self, queryset=None, items=None):
        shop = plata.shop_instance()

        if not queryset:
            queryset = shop.product_model._default_manager.all()

        variations = ProductVariation.objects.all()
        orderitems = shop.orderitem_model.objects.all()

        if items:
            variations = variations.filter(id__in=[item.variation_id for item in items])
            orderitems = orderitems.filter(id__in=[item.id for item in items])

        for key, parameters in self.config.items():
            parameters = dict((str(k), v) for k, v in parameters.items())

            cfg = dict(self.CONFIG_OPTIONS)[key]

            if 'variation_query' in cfg:
                variations = variations.filter(cfg['variation_query'](**parameters))
            if 'orderitem_query' in cfg:
                orderitems = orderitems.filter(cfg['orderitem_query'](**parameters))

        return queryset.filter(id__in=variations.values('product_id')).filter(id__in=orderitems.values('id'))

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
        eligible_products = self.eligible_products(items=items).values_list('id', flat=True)

        eligible_items = [item for item in items if item.variation.product_id in eligible_products]

        if tax_included:
            # TODO how should this value be calculated in the presence of multiple tax rates?
            tax_rate = items[0].tax_class.rate
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
        eligible_products = self.eligible_products(items=items).values_list('id', flat=True)

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


class DiscountProcessor(ProcessorBase):
    def process(self, instance, items):
        for applied in instance.applied_discounts.all():
            applied.apply(instance, items)
