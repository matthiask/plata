from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from . import models


admin.site.register(models.Period,
    list_display=('name', 'notes', 'start'),
    )

admin.site.register(models.StockTransaction,
    date_hierarchy='created',
    list_display=('period', 'created', 'product', 'type', 'change', 'order'),
    list_display_links=('created',),
    list_filter=('period', 'type'),
    raw_id_fields=('product',),
    )
