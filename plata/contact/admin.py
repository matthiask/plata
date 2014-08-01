from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from . import models


class ContactAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('created', 'user', 'dob', 'currency')}),
        (_('Billing address'), {
            'fields': models.Contact.address_fields('billing_'),
        }),
        (_('Shipping address'), {
            'fields': (
                ['shipping_same_as_billing']
                + models.Contact.address_fields('shipping_')),
        }),
        (_('Additional fields'), {
            'fields': ('notes',),
        }),
    )
    list_display = (
        'user', 'billing_first_name', 'billing_last_name',
        'billing_city', 'created')
    list_filter = ('user__is_active',)
    ordering = ('-created',)
    raw_id_fields = ('user',)
    search_fields = (
        ['user__first_name', 'user__last_name', 'user__email']
        + models.Contact.address_fields('billing_')
        + models.Contact.address_fields('shipping_')
    )


admin.site.register(models.Contact, ContactAdmin)
