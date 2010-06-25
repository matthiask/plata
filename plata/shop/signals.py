from django.dispatch import Signal

contact_created = Signal(providing_args=['user', 'contact', 'request'])
order_confirmed = Signal(providing_args=['order', 'request'])
order_completed = Signal(providing_args=['order', 'payment'])
