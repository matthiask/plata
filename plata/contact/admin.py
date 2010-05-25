from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from . import models


class ContactUserInline(admin.TabularInline):
    model = models.ContactUser
    max_num = 1
    raw_id_fields = ('user',)

admin.site.register(models.Contact,
    fieldsets=(
        (None, {'fields': ('created', 'email', 'dob', 'currency')}),
        (_('Billing address'), {'fields': ('billing_company', 'billing_first_name',
            'billing_last_name', 'billing_address', 'billing_zip_code',
            'billing_city', 'billing_country')}),
        (_('Shipping address'), {'fields': ('shipping_same_as_billing',
            'shipping_company', 'shipping_first_name',
            'shipping_last_name', 'shipping_address', 'shipping_zip_code',
            'shipping_city', 'shipping_country')}),
        (_('Additional fields'), {'fields': ('notes',)}),
        ),
    inlines=[ContactUserInline],
    )

