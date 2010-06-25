from django.core.mail import EmailMessage

from plata.shop import signals


class BaseHandler(object):
    @classmethod
    def register(cls, **kwargs):
        instance = cls(**kwargs)
        signals.contact_created.connect(instance.on_contact_created)
        signals.order_confirmed.connect(instance.on_order_confirmed)
        signals.order_completed.connect(instance.on_order_completed)
        return instance


class ConsoleHandler(BaseHandler):
    def __init__(self, stream):
        self.stream = stream

    def on_contact_created(self, sender, **kwargs):
        print >>self.stream, 'Contact created: %s' % kwargs.get('contact')

    def on_order_confirmed(self, sender, **kwargs):
        print >>self.stream, 'Order confirmed: %s' % kwargs.get('order')

    def on_order_completed(self, sender, **kwargs):
        print >>self.stream, 'Order completed: %s, payment %s' % (
            kwargs.get('order'), kwargs.get('payment'))
