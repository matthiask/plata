from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from feincms.models import Base

from plata.product.models import Product


class CMSProduct(Product, Base):
    pass

CMSProduct.register_regions(
    ('german', _('German')),
    ('english', _('English')),
    ('french', _('French')),
    )

from feincms.content.raw.models import RawContent
CMSProduct.create_content_type(RawContent)
