import StringIO

from django.contrib.sites.models import Site
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

import plata
from plata.reporting.order import PDFDocument, invoice_pdf, packing_slip_pdf
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

    def on_contact_created(self, sender, **kwargs): pass
    def on_order_confirmed(self, sender, **kwargs): pass
    def on_order_completed(self, sender, **kwargs): pass


class ConsoleHandler(BaseHandler):
    def __init__(self, stream):
        self.stream = stream

    def on_contact_created(self, sender, **kwargs):
        print >>self.stream, 'Contact created: %(contact)s, password %(password)s' % kwargs

    def on_order_confirmed(self, sender, **kwargs):
        print >>self.stream, 'Order confirmed: %(order)s' % kwargs

    def on_order_completed(self, sender, **kwargs):
        print >>self.stream, 'Order completed: %s, payment %s, new discount %s' % (
            kwargs.get('order'),
            kwargs.get('payment'),
            kwargs.get('remaining_discount'))


class EmailHandler(BaseHandler):
    def context(self, kwargs):
        ctx = {
            'site': Site.objects.get_current(),
            }
        ctx.update(kwargs)
        return ctx

    def on_contact_created(self, sender, **kwargs):
        contact = kwargs['contact']
        email = render_to_string('plata/notifications/contact_created.txt',
            self.context(kwargs)).splitlines()

        message = EmailMessage(
            subject=email[0],
            body=u'\n'.join(email[2:]),
            to=[contact.user.email],
            bcc=plata.settings.PLATA_ALWAYS_BCC,
            )
        message.send()

    def on_order_completed(self, sender, **kwargs):
        order = kwargs['order']
        email = render_to_string('plata/notifications/order_completed.txt',
            self.context(kwargs)).splitlines()

        content = StringIO.StringIO()
        pdf = PDFDocument(content)
        invoice_pdf(pdf, order)

        message = EmailMessage(
            subject=email[0],
            body=u'\n'.join(email[2:]),
            to=[order.email],
            bcc=plata.settings.PLATA_ALWAYS_BCC + plata.settings.PLATA_ORDER_BCC,
            )
        message.attach('invoice-%09d.pdf' % order.id, content.getvalue(), 'application/pdf')
        message.send()

        email = render_to_string('plata/notifications/packing_slip.txt',
            self.context(kwargs)).splitlines()

        content = StringIO.StringIO()
        pdf = PDFDocument(content)
        packing_slip_pdf(pdf, order)

        message = EmailMessage(
            subject='packing slip',
            body=u'',
            to=plata.settings.PLATA_SHIPPING_INFO,
            bcc=plata.settings.PLATA_ALWAYS_BCC + plata.settings.PLATA_ORDER_BCC,
            )
        message.attach('packing-slip-%09d.pdf' % order.id, content.getvalue(), 'application/pdf')
        message.send()

