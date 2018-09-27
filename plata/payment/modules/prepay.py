"""
Payment module for bank transfer in advance
(copy of the check module, just without mentioning checks)

Author: jpbraun@mandriva.com

Configuration:
PLATA_PAYMENT_PREPAY_NOTIFICATIONS
"""
from __future__ import absolute_import, unicode_literals

import logging
from decimal import Decimal
from uuid import uuid4

from django.utils.translation import ugettext_lazy as _
from django.http import Http404, HttpResponse
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site

import plata
from plata.payment.modules.base import ProcessorBase
from plata.shop.models import Order, OrderPayment


logger = logging.getLogger("plata.payment.prepay")


class PaymentProcessor(ProcessorBase):
    key = "prepay"
    default_name = _("Bank transfer in advance")

    def get_urls(self):
        from django.conf.urls import url

        return [
            url(
                r"^payment/prepay/confirm/(?P<uuid>[^/]+)/$",
                self.confirm,
                name="plata_payment_prepay_confirm",
            )
        ]

    def process_order_confirmed(self, request, order):
        if not order.balance_remaining:
            return self.already_paid(order)

        logger.info(
            "Processing order %s using bank transfer in advance (prepay)" % order
        )

        payment = self.create_pending_payment(order)

        order.notes = str(uuid4())
        order.save()

        if plata.settings.PLATA_STOCK_TRACKING:
            StockTransaction = plata.stock_model()
            self.create_transactions(
                order,
                _("sale"),
                type=StockTransaction.SALE,
                negative=True,
                payment=payment,
            )
        current_site = Site.objects.get_current()
        confirm_link = "https://%s%s" % (
            current_site.domain,
            reverse("plata_payment_prepay_confirm", kwargs={"uuid": order.notes}),
        )
        message = _(
            """The order %(order)s has been confirmed for bank transfer in advance.

Customer: %(first_name)s %(last_name)s <%(email)s>

Items: %(items)s

Amount due: %(remaining)s %(currency)s

Click on this link when the payment is received: %(confirm_link)s
"""
            % {
                "order": order,
                "first_name": order.user.first_name,
                "last_name": order.user.last_name,
                "email": order.email,
                "items": ", ".join(("%s" % item) for item in order.items.all()),
                "remaining": order.balance_remaining,
                "currency": order.currency,
                "confirm_link": confirm_link,
            }
        )

        try:
            notification_emails = settings.PLATA_PAYMENT_PREPAY_NOTIFICATIONS.get(
                order.currency
            )
        except KeyError:
            notification_emails = settings.PLATA_PAYMENT_PREPAY_NOTIFICATIONS
        except AttributeError:
            raise Exception(
                _(
                    "Configure the notification emails in the"
                    " PLATA_PAYMENT_PREPAY_NOTIFICATIONS setting"
                )
            )

        send_mail(
            _(
                "%(prefix)sNew order on bank transfer (%(order)s)"
                % {
                    "prefix": getattr(settings, "EMAIL_SUBJECT_PREFIX", ""),
                    "order": order,
                }
            ),
            message,
            settings.SERVER_EMAIL,
            notification_emails,
        )

        return self.shop.render(
            request,
            "payment/prepay_informations.html",
            {
                "order": order,
                "payment": payment,
                "HTTP_HOST": request.META.get("HTTP_HOST"),
            },
        )

    def confirm(self, request, uuid):

        try:
            order = Order.objects.get(notes=uuid)
        except Order.DoesNotExist:
            raise Http404

        payment = list(order.payments.all()[:1])[0]

        if payment.status == OrderPayment.AUTHORIZED:
            return HttpResponse("Already authorized")

        payment.authorized = timezone.now()
        payment.status = OrderPayment.AUTHORIZED
        payment.amount = Decimal(order.balance_remaining)
        payment.currency = order.currency
        payment.payment_method = self.name
        payment.save()
        order.paid = order.total
        order.save()

        self.order_paid(order, payment=payment)
        return HttpResponse("Order authorized")
