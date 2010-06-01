from django.utils.translation import get_language, ugettext_lazy as _

from feincms.content.medialibrary.models import MediaFileContent
from feincms.content.raw.models import RawContent
from feincms.models import ContentProxy

from plata.product.feincms.models import CMSProduct


class RegionTranslationContentProxy(ContentProxy):
    def get_content(self, item, attr):
        try:
            region = item.template.regions_dict['%s_%s' % (attr, get_language()[:2])]
        except KeyError:
            return []

        return sorted(item._content_for_region(region), key=lambda c: c.ordering)


CMSProduct.content_proxy_class = RegionTranslationContentProxy
CMSProduct.register_regions(
    ('main_de', _('German')),
    #('main_en', _('English')),
    #('main_fr', _('French')),
    )

CMSProduct.create_content_type(MediaFileContent, POSITION_CHOICES=(
    ('default', _('default')),
    ))
CMSProduct.create_content_type(RawContent)
