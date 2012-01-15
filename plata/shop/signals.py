"""
Signals sent by the Plata during the checkout process
=====================================================
"""

from django.dispatch import Signal

#: Emitted upon contact creation. Receives the user and contact instance
#: and the new password in cleartext.
contact_created = Signal(providing_args=['user', 'contact', 'password'])

#: Emitted upon order confirmation. Receives an order instance.
order_confirmed = Signal(providing_args=['order'])

#: Emitted upon order completion. Receives the order and payment instances
#: and the remaining discount, if there is any.
order_completed = Signal(providing_args=['order', 'payment', 'remaining_discount'])
