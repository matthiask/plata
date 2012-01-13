from django import template

from plata.product.modules.options.models import Product


register = template.Library()


@register.simple_tag
def featured_products_for_categories(category_list, variable_name='featured_product'):
    """
    {% featured_products_for_categories category_list "variable_name" %}
    """

    product_qset = Product.objects.active()
    category_list = list(category_list)

    for category in category_list:
        try:
            setattr(category, variable_name, product_qset.filter(
                categories=category).order_by('-is_featured', 'ordering', 'name')[0])
        except IndexError:
            pass

    return u''


class BestsellersNode(template.Node):
    def __init__(self, as_):
        self.as_ = as_

    def render(self, context):
        context[self.as_] = Product.objects.bestsellers()[:5]
        return u''


@register.tag
def bestsellers(parser, token):
    """
    Write bestsellers into specified context variable::

        {% bestsellers as product_list %}
    """
    tag, xx, as_ = token.contents.split()
    return BestsellersNode(as_)

"""
Django 1.3::

    @register.simple_tag(needs_context=True)
    def bestsellers(context, variable):
        context[variable] = Product.objects.bestsellers()[:5]
        return u''
"""

