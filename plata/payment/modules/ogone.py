"""
Payment module for Ogone integration

Needs the following settings to work correctly::

    OGONE = {
        'PSPID': 'your_shop_id',
        'LIVE': True, # Or False
        'SHA1_IN': 'yourhash',
        'SHA1_OUT': 'yourotherhash',
        }
"""

import locale
import logging
from decimal import Decimal
from hashlib import sha1

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import get_language, gettext_lazy as _, to_locale
from django.views.decorators.csrf import csrf_exempt

import plata
from plata.payment.modules.base import ProcessorBase
from plata.shop.models import OrderPayment


logger = logging.getLogger("plata.payment.ogone")

csrf_exempt_m = method_decorator(csrf_exempt)


# Copied from ogone test account backend
STATUSES = """\
0	Incomplete or invalid
1	Cancelled by client
2	Authorization refused
4	Order stored
40	Stored waiting external result
41	Waiting client payment
5	Authorized
50	Authorized waiting external result
51	Authorization waiting
52	Authorization not known
55	Stand-by
56	OK with scheduled payments
57	Error in scheduled payments
59	Authoriz. to get manually
6	Authorized and cancelled
61	Author. deletion waiting
62	Author. deletion uncertain
63	Author. deletion refused
64	Authorized and cancelled
7	Payment deleted
71	Payment deletion pending
72	Payment deletion uncertain
73	Payment deletion refused
74	Payment deleted
75	Deletion processed by merchant
8	Refund
81	Refund pending
82	Refund uncertain
83	Refund refused
84	Payment declined by the acquirer
85	Refund processed by merchant
9	Payment requested
91	Payment processing
92	Payment uncertain
93	Payment refused
94	Refund declined by the acquirer
95	Payment processed by merchant
99	Being processed"""

STATUS_DICT = dict(line.split("\t") for line in STATUSES.splitlines())


class PaymentProcessor(ProcessorBase):
    key = "ogone"
    default_name = _("Ogone")

    def get_urls(self):
        from django.urls import path

        return [path("payment/ogone/ipn/", self.ipn, name="plata_payment_ogone_ipn")]

    def process_order_confirmed(self, request, order):
        OGONE = settings.OGONE

        if not order.balance_remaining:
            return self.already_paid(order, request=request)

        logger.info("Processing order %s using Ogone" % order)

        payment = self.create_pending_payment(order)
        if plata.settings.PLATA_STOCK_TRACKING:
            StockTransaction = plata.stock_model()
            self.create_transactions(
                order,
                _("payment process reservation"),
                type=StockTransaction.PAYMENT_PROCESS_RESERVATION,
                negative=True,
                payment=payment,
            )

        # params that will be hashed
        form_params = {
            "PSPID": OGONE["PSPID"],
            "orderID": "Order-%d-%d" % (order.id, payment.id),
            "amount": "%s"
            % int(order.balance_remaining.quantize(Decimal("0.00")) * 100),
            "currency": order.currency,
            "language": locale.normalize(to_locale(get_language())).split(".")[0],
            "CN": f"{order.billing_first_name} {order.billing_last_name}",
            "EMAIL": order.email,
            "ownerZIP": order.billing_zip_code,
            "owneraddress": order.billing_address,
            "ownertown": order.billing_city,
            "accepturl": "http://{}{}".format(
                request.get_host(), reverse("plata_order_success")
            ),
            "declineurl": "http://{}{}".format(
                request.get_host(), reverse("plata_order_payment_failure")
            ),
            "exceptionurl": "http://{}{}".format(
                request.get_host(), reverse("plata_order_payment_failure")
            ),
            "cancelurl": "http://{}{}".format(
                request.get_host(), reverse("plata_order_payment_failure")
            ),
        }
        # create hash
        value_strings = [
            "{}={}{}".format(key.upper(), value, OGONE["SHA1_IN"])
            for key, value in form_params.items()
        ]
        hash_string = "".join(sorted(value_strings))
        encoded_hash_string = sha1(hash_string.encode("utf-8")).hexdigest()

        # add hash and additional params
        form_params.update(
            {
                "SHASign": encoded_hash_string.upper(),
                "mode": OGONE["LIVE"] and "prod" or "test",
            }
        )

        return self.shop.render(
            request,
            "payment/%s_form.html" % self.key,
            {
                "order": order,
                "HTTP_HOST": request.get_host(),
                "form_params": form_params,
                "locale": form_params["language"],
            },
        )

    @csrf_exempt_m
    def ipn(self, request):
        OGONE = settings.OGONE

        try:
            parameters_repr = repr(request.POST.copy()).encode("utf-8")
            logger.info("IPN: Processing request data %s" % parameters_repr)

            try:
                orderID = request.POST["orderID"]
                currency = request.POST["currency"]
                amount = request.POST["amount"]
                STATUS = request.POST["STATUS"]
                PAYID = request.POST["PAYID"]
                BRAND = request.POST["BRAND"]
                SHASIGN = request.POST["SHASIGN"]
            except KeyError:
                logger.error("IPN: Missing data in %s" % parameters_repr)
                return HttpResponseForbidden("Missing data")

            value_strings = [
                "{}={}{}".format(key.upper(), value, OGONE["SHA1_OUT"])
                for key, value in request.POST.items()
                if value and key != "SHASIGN"
            ]
            sha1_out = sha1(
                ("".join(sorted(value_strings))).encode("utf-8")
            ).hexdigest()

            if sha1_out.lower() != SHASIGN.lower():
                logger.error("IPN: Invalid hash in %s" % parameters_repr)
                return HttpResponseForbidden("Hash did not validate")

            try:
                order, order_id, payment_id = orderID.split("-")
            except ValueError:
                logger.error("IPN: Error getting order for %s" % orderID)
                return HttpResponseForbidden("Malformed order ID")

            # Try fetching the order and order payment objects
            # We create a new order payment object in case the old one
            # cannot be found.
            try:
                order = self.shop.order_model.objects.get(pk=order_id)
            except self.shop.order_model.DoesNotExist:
                logger.error("IPN: Order %s does not exist" % order_id)
                return HttpResponseForbidden("Order %s does not exist" % order_id)

            try:
                payment = order.payments.get(pk=payment_id)
            except order.payments.model.DoesNotExist:
                payment = order.payments.model(
                    order=order, payment_module="%s" % self.name
                )

            payment.status = OrderPayment.PROCESSED
            payment.currency = currency
            payment.amount = Decimal(amount)
            payment.data = request.POST.copy()
            payment.transaction_id = PAYID
            payment.payment_method = BRAND
            payment.notes = STATUS_DICT.get(STATUS)

            if STATUS in ("5", "9"):
                payment.authorized = timezone.now()
                payment.status = OrderPayment.AUTHORIZED

            payment.save()
            order = order.reload()

            logger.info("IPN: Successfully processed IPN request for %s" % order)

            if payment.authorized and plata.settings.PLATA_STOCK_TRACKING:
                StockTransaction = plata.stock_model()
                self.create_transactions(
                    order,
                    _("sale"),
                    type=StockTransaction.SALE,
                    negative=True,
                    payment=payment,
                )

            if not order.balance_remaining:
                self.order_paid(order, payment=payment, request=request)

            return HttpResponse("OK")
        except Exception as e:
            logger.error("IPN: Processing failure %s" % e)
            raise
