from django.utils.translation import get_language, ugettext_lazy as _

from feincms.models import Base

from plata.product.models import Product, ProductManager


class CMSProduct(Product, Base):
    class Meta:
        app_label = 'product'
        verbose_name = _('product')
        verbose_name_plural = _('products')

    objects = ProductManager()
