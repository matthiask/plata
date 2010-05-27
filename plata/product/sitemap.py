from django.contrib.sitemaps import Sitemap

from models import Product

class ProductSitemap(Sitemap):
    def items(self):
        return Product.objects.active().select_related()