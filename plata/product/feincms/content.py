from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.db import models
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _


import plata
from plata.product.models import Category


class ProductList(models.Model):
    only_featured = models.BooleanField(_('featured only'))
    only_sale = models.BooleanField(_('sales only'))
    categories = models.ManyToManyField(Category, blank=True, null=True,
        verbose_name=_('categories'))
    paginate_by = models.PositiveIntegerField(_('paginate by'), default=0,
        help_text=_('Set to 0 to disable pagination.'))

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

        my_ctx = {'object_list': products}

        if self.paginate_by:
            paginator = Paginator(products, self.paginate_by)

            try:
                page = int(request.GET.get('page'))
            except (TypeError, ValueError):
                page = 1

            try:
                products = paginator.page(page)
            except (EmptyPage, InvalidPage):
                products = paginator.page(paginator.num_pages)

            my_ctx['page'] = products
            my_ctx['object_list'] = products.object_list

        return render_to_string('product/product_list.html', my_ctx,
            context_instance=context)
