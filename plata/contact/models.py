from datetime import datetime

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _

from plata.fields import CurrencyField
from plata.shop.models import BillingShippingAddress


class Contact(BillingShippingAddress):
    """
    Each user can have at most one of these

    Note: You do not have to use this model if you want to store the contact
    information somewhere else. If you use your own contact model, you should
    take care of two things:

    - ``Contact.update_from_order`` has to exist, and should fill in
      contact details from the order
    - You probably have to override ``Shop.checkout_form`` too - this method
      probably won't work for your custom contact model
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

    def update_from_order(self, order, request=None):
        """
        This method is called by the checkout step and is used to update
        the contact information from an order instance
        """

        self.currency = order.currency
        self.shipping_same_as_billing = order.shipping_same_as_billing

        for field in self.ADDRESS_FIELDS:
            f = 'shipping_' + field
            setattr(self, f, getattr(order, f))

            f = 'billing_' + field
            setattr(self, f, getattr(order, f))
