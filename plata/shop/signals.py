from django.dispatch import Signal

contact_created = Signal(providing_args=['user', 'contact'])
order_confirmed = Signal(providing_args=['order'])
order_completed = Signal(providing_args=['order', 'payment', 'remaining_discount'])
