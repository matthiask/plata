from __future__ import absolute_import, unicode_literals

from django.dispatch import Signal

#: Emitted upon contact creation. Receives the user and contact instance
#: and the new password in cleartext.
contact_created = Signal(
    providing_args=['user', 'contact', 'password', 'request'],
)

#: Emitted upon order confirmation. Receives an order instance.
order_confirmed = Signal(
    providing_args=['order', 'request'],
)

#: Emitted when an order has been completely paid for. Receives the order
#: and payment instances and the remaining discount amount excl. tax, if
#: there is any.
order_paid = Signal(
    providing_args=['order', 'payment', 'remaining_discount', 'request'],
)
