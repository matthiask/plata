from django.core.mail import EmailMessage

from plata.shop import signals


class BaseHandler(object):
    @classmethod
    def register(cls, **kwargs):
        instance = cls(**kwargs)

        dispatch_uid = kwargs.get('dispatch_uid', cls.__name__)

        signals.contact_created.connect(instance.on_contact_created,
            dispatch_uid=dispatch_uid)
        signals.order_confirmed.connect(instance.on_order_confirmed,
            dispatch_uid=dispatch_uid)
        signals.order_completed.connect(instance.on_order_completed,
            dispatch_uid=dispatch_uid)

        return instance

    def on_contact_created(self, sender, **kwargs):
        pass

    def on_order_confirmed(self, sender, **kwargs):
        pass

    def on_order_completed(self, sender, **kwargs):
        pass


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


class EmailHandler(BaseHandler):
    def on_contact_created(self, sender, **kwargs):
        contact = kwargs.get('contact')
        if not contact:
            return

        message = EmailMessage(
            subject='Account created',
            body='Your account has been created.',
            to=[contact.user.email],
            )
        message.send()

    def on_order_confirmed(self, sender, **kwargs):
        pass

    def on_order_completed(self, sender, **kwargs):
        order = kwargs.get('order')
        if not order:
            return

        message = EmailMessage(
            subject='Order completed',
            body='Your order has been successfully paid.',
            to=[order.email],
            )
        message.send()
