from django import template

import plata


register = template.Library()


@register.simple_tag
def featured_products_for_categories(category_list, variable_name='featured_product'):
    """
    {% featured_products_for_categories category_list "variable_name" %}
    """

    category_list = list(category_list)

    for category in category_list:
        try:
            setattr(category, variable_name, category.products.active().order_by('-is_featured')[0])
        except IndexError:
            pass

    return u''
