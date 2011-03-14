from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.db import models
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _


import plata
from plata.product.models import Category


class CategoryList(models.Model):
    """
    FeinCMS content type showing a list of categories

    Does not depend on the FeinCMS-based product model.
    """

    subcategories_of = models.ForeignKey(Category, blank=True, null=True,
        verbose_name=_('subcategories of'),
        limit_choices_to={'parent__isnull': True},
        help_text=_('Only top-level categories are shown if left empty.'),
        )

    class Meta:
        abstract = True
        verbose_name = _('category list')
        verbose_name_plural = _('category lists')

    def render(self, request, context, **kwargs):
        categories = Category.objects.public()
        if self.subcategories_of:
            categories = categories.filter(parent=self.subcategories_of)

        return render_to_string('product/category_list.html', {
            'content': self,
            'object_list': categories,
        }, context_instance=context)


class ProductList(models.Model):
    """
    FeinCMS content type showing a list of products

    Does not depend on the FeinCMS-based product model.
    """

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
            currency = shop.default_currency(request=request)
            products = [p for p in products if p.in_sale(currency)]

        my_ctx = {'content': self, 'object_list': products}

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
