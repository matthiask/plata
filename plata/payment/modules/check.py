"""
Payment module for check/transfer

Author: jpbraun@mandriva.com

Configuration:
PLATA_PAYMENT_CHECK_NOTIFICATIONS
"""

import logging
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.http import Http404, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

import plata
from plata.payment.modules.base import ProcessorBase
from plata.shop.models import Order, OrderPayment


logger = logging.getLogger("plata.payment.check")


class PaymentProcessor(ProcessorBase):
    key = "check"
    default_name = _("Check/Bank transfer")

    def get_urls(self):
        from django.urls import path

        return [
            path(
                "payment/check/confirm/<str:uuid>/",
                self.confirm,
                name="plata_payment_check_confirm",
            )
        ]

    def process_order_confirmed(self, request, order):
        if not order.balance_remaining:
            return self.already_paid(order)

        logger.info("Processing order %s using check" % order)

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
        confirm_link = "https://{}{}".format(
            current_site.domain,
            reverse("plata_payment_check_confirm", kwargs={"uuid": order.notes}),
        )
        message = _(
            """The order {order} has been confirmed for check or bank transfer.

Customer: {first_name} {last_name} <{email}>

Items: {items}

Amount due: {remaining} {currency}

Click on this link when the payment is received: {confirm_link}
""".format(
                order=order,
                first_name=order.user.first_name,
                last_name=order.user.last_name,
                email=order.email,
                items=", ".join(("%s" % item) for item in order.items.all()),
                remaining=order.balance_remaining,
                currency=order.currency,
                confirm_link=confirm_link,
            )
        )

        try:
            notification_emails = settings.PLATA_PAYMENT_CHECK_NOTIFICATIONS.get(
                order.currency
            )
        except KeyError:
            notification_emails = settings.PLATA_PAYMENT_CHECK_NOTIFICATIONS
        except AttributeError:
            raise Exception(
                _(
                    "Configure the notification emails in the"
                    " PLATA_PAYMENT_CHECK_NOTIFICATIONS setting"
                )
            )

        send_mail(
            _(
                "{prefix}New check/bank order ({order})".format(
                    prefix=getattr(settings, "EMAIL_SUBJECT_PREFIX", ""),
                    order=order,
                )
            ),
            message,
            settings.SERVER_EMAIL,
            notification_emails,
        )

        return self.shop.render(
            request,
            "payment/check_informations.html",
            {
                "order": order,
                "payment": payment,
                "HTTP_HOST": request.headers.get("host"),
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
