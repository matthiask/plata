from __future__ import absolute_import, unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from plata.shop import forms as shop_forms
from plata.shop.models import Order


class CheckoutForm(shop_forms.BaseCheckoutForm):
    class Meta:
        fields = ['notes', 'email', 'shipping_same_as_billing']
        fields.extend('billing_%s' % f for f in Order.ADDRESS_FIELDS)
        fields.extend('shipping_%s' % f for f in Order.ADDRESS_FIELDS)
        model = Order

    def __init__(self, *args, **kwargs):
        # BaseCheckoutForm.__init__ needs the following kwargs too, because
        # of this we do not pop() them here
        shop = kwargs.get('shop')
        request = kwargs.get('request')

        self.REQUIRED_ADDRESS_FIELDS = shop.contact_model.ADDRESS_FIELDS[:]
        self.REQUIRED_ADDRESS_FIELDS.remove('company')

        contact = shop.contact_from_user(request.user)

        if contact:
            initial = {
                'email': contact.user.email,
                'shipping_same_as_billing': contact.shipping_same_as_billing,
            }

            for f in contact.ADDRESS_FIELDS:
                initial['billing_%s' % f] = getattr(
                    contact,
                    'billing_%s' % f)
                initial['shipping_%s' % f] = getattr(
                    contact,
                    'shipping_%s' % f)

            kwargs['initial'] = initial

        elif request.user.is_authenticated():
            kwargs['initial'] = {
                'email': request.user.email,
                'billing_first_name': request.user.first_name,
                'billing_last_name': request.user.last_name,
            }

        super(CheckoutForm, self).__init__(*args, **kwargs)

        if not (contact or request.user.is_authenticated()):
            self.fields['create_account'] = forms.BooleanField(
                label=_('create account'),
                required=False, initial=True)

    def clean(self):
        data = super(CheckoutForm, self).clean()

        if not data.get('shipping_same_as_billing'):
            for f in self.REQUIRED_ADDRESS_FIELDS:
                field = 'shipping_%s' % f
                if not data.get(field):
                    self._errors[field] = self.error_class([
                        _('This field is required.')])

        return data
