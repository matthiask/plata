from datetime import datetime

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _

from plata.fields import CurrencyField


class BillingShippingAddress(models.Model):
    """
    Abstract base class for all models storing a billing and a shipping address
    """

    ADDRESS_FIELDS = ['company', 'first_name', 'last_name', 'address',
        'zip_code', 'city', 'country']

    billing_company = models.CharField(_('company'), max_length=100, blank=True)
    billing_first_name = models.CharField(_('first name'), max_length=100)
    billing_last_name = models.CharField(_('last name'), max_length=100)
    billing_address = models.TextField(_('address'))
    billing_zip_code = models.CharField(_('ZIP code'), max_length=50)
    billing_city = models.CharField(_('city'), max_length=100)
    billing_country = models.CharField(_('country'), max_length=3, blank=True)

    shipping_same_as_billing = models.BooleanField(_('shipping address equals billing address'),
        default=True)

    shipping_company = models.CharField(_('company'), max_length=100, blank=True)
    shipping_first_name = models.CharField(_('first name'), max_length=100, blank=True)
    shipping_last_name = models.CharField(_('last name'), max_length=100, blank=True)
    shipping_address = models.TextField(_('address'), blank=True)
    shipping_zip_code = models.CharField(_('ZIP code'), max_length=50, blank=True)
    shipping_city = models.CharField(_('city'), max_length=100, blank=True)
    shipping_country = models.CharField(_('country'), max_length=3, blank=True)

    class Meta:
        abstract = True

    def addresses(self):
        billing = dict((f, getattr(self, 'billing_%s' % f)) for f in self.ADDRESS_FIELDS)

        if self.shipping_same_as_billing:
            shipping = billing
        else:
            shipping = dict((f, getattr(self, 'shipping_%s' % f)) for f in self.ADDRESS_FIELDS)

        return {'billing': billing, 'shipping': shipping}


class Contact(BillingShippingAddress):
    """
    Each user can have at most one of these
    """

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
