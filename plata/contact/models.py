from datetime import datetime

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _

from plata.fields import CurrencyField
from plata.shop.models import BillingShippingAddress


class ContactManager(models.Manager):
    def create_from_order(self, order, user):
        contact = self.model(user=user, currency=order.currency)

        for field in self.model.ADDRESS_FIELDS:
            f = 'shipping_' + field
            setattr(contact, f, getattr(order, f))

            f = 'billing_' + field
            setattr(contact, f, getattr(order, f))

        contact.shipping_same_as_billing = order.shipping_same_as_billing
        contact.save()
        return contact


class Contact(BillingShippingAddress):
    """
    Each user can have at most one of these

    Note: You do not have to use this model if you want to store the contact
    information somewhere else. If you use your own contact model, you should
    take care of two things:

    - ``Contact.objects.create_from_order`` has to exist, and should fill in
      contact details from the order
    - ``Contact.ADDRESS_FIELDS`` should exist; if it does not you'll have to
      override ``Shop.checkout_form``
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

    objects = ContactManager()

    def __unicode__(self):
        return unicode(self.user)
