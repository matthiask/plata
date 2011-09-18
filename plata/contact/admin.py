from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from . import models


admin.site.register(models.Contact,
    fieldsets=(
        (None, {'fields': ('created', 'user', 'dob', 'currency')}),
        (_('Billing address'), {'fields': models.Contact.address_fields('billing_')}),
        (_('Shipping address'), {'fields': ['shipping_same_as_billing'] +\
            models.Contact.address_fields('shipping_')}),
        (_('Additional fields'), {'fields': ('notes',)}),
        ),
    search_fields=(['user__first_name', 'user__last_name', 'user__email'] +
        models.Contact.address_fields('billing_') +
        models.Contact.address_fields('shipping_')
        ),
    )
