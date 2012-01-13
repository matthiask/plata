from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from plata.discount.models import DiscountBase


def explicit_products(product_model):
    """
    Explicitly define products eligible for discounting

    Example::

        from ... import Product
        explicit_products(Product)
    """

    DiscountBase.CONFIG_OPTIONS.append(('products', {
        'title': _('Explicitly define discountable products'),
        'form_fields': [
            ('products', forms.ModelMultipleChoiceField(
                product_model._default_manager.all(),
                label=_('products'),
                required=True,
                widget=FilteredSelectMultiple(
                    verbose_name=_('products'),
                    is_stacked=False,
                    ),
                )),
            ],
        'product_query': lambda products: Q(product__in=products),
        }))


def only_categories(category_model):
    """
    Define categories whose products are eligible for discounting

    Example::

        from ... import Product
        only_categories(Product)
    """

    DiscountBase.CONFIG_OPTIONS.append(('only_categories', {
        'title': _('Only products from selected categories'),
        'form_fields': [
            ('categories', forms.ModelMultipleChoiceField(
                category_model._default_manager.all(),
                label=_('categories'),
                required=True,
                widget=FilteredSelectMultiple(
                    verbose_name=_('categories'),
                    is_stacked=False,
                    ),
                )),
            ],
        'product_query': lambda categories: Q(product__categories__in=categories),
        }))
