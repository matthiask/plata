from datetime import datetime

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _

from cldr_countries.fields import CountryField

from plata.fields import CurrencyField


class BillingShippingAddress(models.Model):
    ADDRESS_FIELDS = ['company', 'first_name', 'last_name', 'address',
        'zip_code', 'city', 'country']

    billing_company = models.CharField(_('company'), max_length=100, blank=True)
    billing_first_name = models.CharField(_('first name'), max_length=100)
    billing_last_name = models.CharField(_('last name'), max_length=100)
    billing_address = models.TextField(_('address'))
    billing_zip_code = models.CharField(_('ZIP code'), max_length=50)
    billing_city = models.CharField(_('city'), max_length=100)
    billing_country = CountryField()

    shipping_same_as_billing = models.BooleanField(_('shipping address equals billing address'),
        default=True)

    shipping_company = models.CharField(_('company'), max_length=100, blank=True)
    shipping_first_name = models.CharField(_('first name'), max_length=100, blank=True)
    shipping_last_name = models.CharField(_('last name'), max_length=100, blank=True)
    shipping_address = models.TextField(_('address'), blank=True)
    shipping_zip_code = models.CharField(_('ZIP code'), max_length=50, blank=True)
    shipping_city = models.CharField(_('city'), max_length=100, blank=True)
    shipping_country = CountryField(blank=True)

    class Meta:
        abstract = True

    def copy_address(self, instance=None):
        instance = instance or self.instance

        self.shipping_same_as_billing = instance.shipping_same_as_billing

        for field in self.ADDRESS_FIELDS:
            setattr(self, 'billing_%s' % field,
                getattr(instance, 'billing_%s' % field))
            setattr(self, 'shipping_%s' % field,
                getattr(instance, 'shipping_%s' % field))


class Contact(BillingShippingAddress):
    user = models.OneToOneField(User, verbose_name=_('user'),
        related_name='contactuser')

    dob = models.DateField(_('date of birth'), blank=True, null=True)
    created = models.DateTimeField(_('created'), default=datetime.now)

    currency = CurrencyField(help_text=_('Preferred currency.'))
    notes = models.TextField(_('notes'), blank=True)

    class Meta:
        verbose_name = _('contact')
        verbose_name_plural = _('contacts')

    def __unicode__(self):
        return unicode(self.user)
