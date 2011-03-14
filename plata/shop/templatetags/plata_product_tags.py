from django import template

import plata


register = template.Library()


@register.simple_tag
def featured_products_for_categories(category_list, variable_name='featured_product'):
    """
    {% featured_products_for_categories category_list "variable_name" %}
    """

    product_qset = plata.shop_instance().product_model.objects.active()
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
        shop = plata.shop_instance()

        context[self.as_] = shop.product_model.objects.bestsellers()[:5]
        return u''


@register.tag
def bestsellers(parser, token):
    """
    Write bestsellers into specified context variable::

        {% bestsellers as product_list %}
    """

    tag, xx, as_ = token.contents.split()

    return BestsellersNode(as_)
