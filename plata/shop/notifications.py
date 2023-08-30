"""
Even though these shop signal handlers might be useful, you might be better
off writing your own handlers for the three important signals:

- ``contact_created``: A new contact has been created during the checkout
  process
- ``order_confirmed``: The order has been confirmed, a payment method has
  been selected
- ``order_paid``: The order is fully paid

A real-world example follows::

    from django.utils.translation import activate

    from plata.shop import notifications, signals as shop_signals


    class EmailHandler(notifications.BaseHandler):
        ALWAYS = ['shopadmin@example.com']
        SHIPPING = ['warehouse@example.com']

        def __call__(self, sender, order, **kwargs):
            cash_on_delivery = False
            try:
                if (order.payments.all()[0].payment_module_key == 'cod'):
                    cash_on_delivery = True
            except:
                pass

            if order.language_code:
                activate(order.language_code)

            invoice_message = self.create_email_message(
                'plata/notifications/order_paid.txt',
                order=order,
                **kwargs)
            invoice_message.attach(order.order_id + '.pdf',
                self.invoice_pdf(order), 'application/pdf')
            invoice_message.to.append(order.email)
            invoice_message.bcc.extend(self.ALWAYS)

            packing_slip_message = self.create_email_message(
                'plata/notifications/packing_slip.txt',
                order=order,
                **kwargs)
            packing_slip_message.attach(
                order.order_id + '-LS.pdf',
                self.packing_slip_pdf(order),
                'application/pdf')
            packing_slip_message.to.extend(self.ALWAYS)

            if cash_on_delivery:
                invoice_message.bcc.extend(self.SHIPPING)
            else:
                packing_slip_message.to.extend(self.SHIPPING)

            invoice_message.send()
            packing_slip_message.send()

    shop_signals.contact_created.connect(
        notifications.ContactCreatedHandler(),
        weak=False)
    shop_signals.order_paid.connect(
        EmailHandler(),
        weak=False)
"""


import contextlib
from io import BytesIO

from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.translation import activate


class BaseHandler:
    def invoice_pdf(self, order):
        from plata.reporting.order import invoice_pdf
        from plata.reporting.pdfdocument import PlataPDFDocument

        with contextlib.closing(BytesIO()) as content:
            pdf = PlataPDFDocument(content)
            invoice_pdf(pdf, order)
            return content.getvalue()

    def packing_slip_pdf(self, order):
        from plata.reporting.order import packing_slip_pdf
        from plata.reporting.pdfdocument import PlataPDFDocument

        with contextlib.closing(BytesIO()) as content:
            pdf = PlataPDFDocument(content)
            packing_slip_pdf(pdf, order)
            return content.getvalue()

    def context(self, ctx, **kwargs):
        request = ctx.get("request")
        if request is not None:
            ctx.update({"site": get_current_site(request)})
        ctx.update(kwargs)
        return ctx

    def create_email_message(self, template_name, **kwargs):
        email = render_to_string(template_name, self.context(kwargs)).splitlines()
        return EmailMessage(subject=email[0], body="\n".join(email[2:]))


class EmailHandler(BaseHandler):
    def __init__(self, always_to=None, always_bcc=None):
        self.always_to = always_to
        self.always_bcc = always_bcc

    def __call__(self, sender, **kwargs):
        email = self.message(sender, **kwargs)

        if self.always_to:
            email.to += list(self.always_to)
        if self.always_bcc:
            email.bcc += list(self.always_bcc)

        # TODO log this, or send a replacement email to the shop owner
        email.send(fail_silently=True)


class ContactCreatedHandler(EmailHandler):
    """
    Send an e-mail message to a newly created contact, optionally BCC'ing
    the addresses passed as ``always_bcc`` upon handler initialization.

    Usage::

        signals.contact_created.connect(
            ContactCreatedHandler(),
            weak=False)

    or::

        signals.contact_created.connect(
            ContactCreatedHandler(always_bcc=['owner@example.com']),
            weak=False)
    """

    def message(self, sender, contact, **kwargs):
        message = self.create_email_message(
            "plata/notifications/contact_created.txt", contact=contact, **kwargs
        )
        message.to.append(contact.user.email)
        return message


class SendInvoiceHandler(EmailHandler):
    """
    Send an e-mail with attached invoice to the customer after successful
    order completion, optionally BCC'ing the addresses passed as
    ``always_bcc`` to the handler upon initialization.

    Usage::

        signals.order_paid.connect(
            SendInvoiceHandler(always_bcc=['owner@example.com']),
            weak=False)
    """

    def message(self, sender, order, **kwargs):
        if order.language_code:
            activate(order.language_code)

        message = self.create_email_message(
            "plata/notifications/order_paid.txt", order=order, **kwargs
        )

        message.to.append(order.email)
        message.attach(
            "invoice-%09d.pdf" % order.id, self.invoice_pdf(order), "application/pdf"
        )
        return message


class SendPackingSlipHandler(EmailHandler):
    """
    Send an e-mail with attached packing slip to the addresses specified upon
    handler initialization. You should pass at least one address in either
    the ``always_to`` or the ``always_bcc`` argument, or else the e-mail
    will go nowhere.

    Usage::

        signals.order_paid.connect(
            SendPackingSlipHandler(always_to=['warehouse@example.com']),
            weak=False)
    """

    def message(self, sender, order, **kwargs):
        if order.language_code:
            activate(order.language_code)

        message = self.create_email_message(
            "plata/notifications/packing_slip.txt", order=order, **kwargs
        )
        message.attach(
            "packing-slip-%09d.pdf" % order.id,
            self.packing_slip_pdf(order),
            "application/pdf",
        )
        return message


"""
from plata.shop import notifications, signals as shop_signals

shop_signals.contact_created.connect(
    notifications.ContactCreatedHandler(always_bcc=[]),
    weak=False)
shop_signals.order_paid.connect(
    notifications.SendInvoiceHandler(always_bcc=[]),
    weak=False)
shop_signals.order_paid.connect(
    notifications.SendPackingSlipHandler(
        always_to=[],
        always_bcc=[]),
    weak=False)
"""
