from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import get_language, ugettext_lazy as _

from feincms.models import Base, ContentProxy

from plata.product.models import Product


class RegionTranslationContentProxy(ContentProxy):
    def get_content(self, item, attr):
        try:
            region = item.template.regions_dict['%s_%s' % (attr, get_language()[:2])]
        except KeyError:
            return []

        return sorted(item._content_for_region(region), key=lambda c: c.ordering)


class CMSProduct(Product, Base):
    content_proxy_class = RegionTranslationContentProxy

CMSProduct.register_regions(
    ('main_de', _('German')),
    ('main_en', _('English')),
    ('main_fr', _('French')),
    )

from feincms.content.raw.models import RawContent
CMSProduct.create_content_type(RawContent)
