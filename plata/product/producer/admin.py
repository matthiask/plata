from django import forms
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from . import models


admin.site.register(models.Producer,
    list_display=('is_active', 'name', 'ordering'),
    list_display_links=('name',),
    search_fields=('name', 'description'),
    )
