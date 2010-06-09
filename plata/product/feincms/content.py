from django.db import models
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _


import plata
from plata.product.models import Category


class ProductList(models.Model):
    only_featured = models.BooleanField(_('featured only'))
    only_sale = models.BooleanField(_('sales only'))
    categories = models.ManyToManyField(Category, blank=True, null=True)

    class Meta:
        abstract = True
        verbose_name = _('product list')
        verbose_name_plural = _('product lists')

    def render(self, request, context, **kwargs):
        shop = plata.shop_instance()
        products = shop.product_model.objects.active()

        if self.only_featured:
            products = products.filter(is_featured=True)

        categories = [c.pk for c in self.categories.all()]
        if categories:
            products = products.filter(categories__in=categories)

        if self.only_sale:
            products = [p for p in products if p.in_sale('CHF')]

        return render_to_string('product/product_list.html', {
            'object_list': products,
            }, context_instance=context)
