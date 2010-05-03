from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from . import models


class OptionInline(admin.TabularInline):
    model = models.Option

admin.site.register(models.OptionGroup,
    inlines=[OptionInline],
    list_display=('name',),
    )

admin.site.register(models.ProductGroup,
    list_display=('primary_product',),
    )
