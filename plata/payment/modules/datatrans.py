"""
Payment module for Datatrans integration

Needs the following settings to work correctly::

    DATATRANS = {
        'MERCHANT_ID': '1000000000000',
        'LIVE': False
        }
"""

import logging
import urllib
from decimal import Decimal
from xml.etree import ElementTree as ET

from django.conf import settings
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt

import plata
from plata.payment.modules.base import ProcessorBase
from plata.shop.models import OrderPayment


logger = logging.getLogger("plata.payment.datatrans")

csrf_exempt_m = method_decorator(csrf_exempt)

SMALLEST_UNIT_FACTOR = 100


class PaymentProcessor(ProcessorBase):
    key = "datatrans"
    default_name = _("Datatrans")

    def enabled_for_request(self, request):
        return True

    def get_urls(self):
        from django.urls import path

        return [
            path(
                "datatrans/success/",
                self.datatrans_success,
                name="plata_payment_datatrans_success",
            ),
            path(
                "datatrans/error/",
                self.datatrans_error,
                name="plata_payment_datatrans_error",
            ),
            path(
                "datatrans/cancel/",
                self.datatrans_cancel,
                name="plata_payment_datatrans_cancel",
            ),
        ]

    def process_order_confirmed(self, request, order):
        DATATRANS = settings.DATATRANS

        if not order.balance_remaining:
            return self.already_paid(order, request=request)

        logger.info("Processing order %s using Datatrans" % order)

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

        if DATATRANS.get("LIVE", True):
            DT_URL = "https://payment.datatrans.biz/upp/jsp/upStart.jsp"
        else:
            DT_URL = "https://pilot.datatrans.biz/upp/jsp/upStart.jsp"

        return render(
            request,
            "payment/datatrans_form.html",
            {
                "order": order,
                "total_in_smallest_unit": payment.amount * SMALLEST_UNIT_FACTOR,
                "payment": payment,
                "HTTP_HOST": request.headers.get("host"),
                "post_url": DT_URL,
                "MERCHANT_ID": DATATRANS["MERCHANT_ID"],
            },
        )

    @csrf_exempt_m
    def datatrans_error(self, request):
        error_code = int(request.POST.get("errorCode"))
        logger.info("Got an error during datatrans payment! code is %s" % error_code)
        return redirect("plata_shop_checkout")

    @csrf_exempt_m
    def datatrans_cancel(self, request):
        logger.info("Canceled transaction")
        return redirect("plata_shop_checkout")

    @csrf_exempt_m
    def datatrans_success(self, request):
        DATATRANS = settings.DATATRANS
        if DATATRANS.get("LIVE", True):
            DT_URL = "https://payment.datatrans.biz/upp/jsp/XML_status.jsp"
        else:
            DT_URL = "https://pilot.datatrans.biz/upp/jsp/XML_status.jsp"

        parameters = None

        try:
            response = None
            parameters = request.POST.copy()
            parameters_repr = repr(parameters).encode("utf-8")
            if parameters:
                logger.info("IPN: Processing request data %s" % parameters_repr)

                xml = """<?xml version="1.0" encoding="UTF-8" ?>
                <statusService version="1">
                  <body merchantId="{merchant_id}">
                    <transaction>
                      <request>
                        <uppTransactionId>{transaction_id}</uppTransactionId>
                      </request>
                    </transaction>
                  </body>
                </statusService>
                """.format(
                    transaction_id=parameters["uppTransactionId"],
                    merchant_id=DATATRANS["MERCHANT_ID"],
                )
                params = urllib.urlencode({"xmlRequest": xml})
                xml_response = urllib.urlopen(DT_URL, params).read()

                tree = ET.fromstring(xml_response)
                response = tree.find("body/transaction/response")
                response_code = response.find("responseCode").text
                if response_code not in ("1", "2", "3"):
                    logger.error(
                        "IPN: Received response_code {}, could not verify parameters {}".format(
                            response_code, parameters_repr
                        )
                    )
                    parameters = None

            if response:
                refno = response.find("refno").text
                currency = response.find("currency").text
                amount = response.find("amount").text
                try:
                    order_id, payment_id = refno.split("-")
                except ValueError:
                    logger.error("IPN: Error getting order for %s" % refno)
                    return HttpResponseForbidden("Malformed order ID")
                try:
                    order = self.shop.order_model.objects.get(pk=order_id)
                except self.shop.order_model.DoesNotExist:
                    logger.error("IPN: Order %s does not exist" % order_id)
                    return HttpResponseForbidden("Order %s does not exist" % order_id)

                try:
                    payment = order.payments.get(pk=payment_id)
                except order.payments.model.DoesNotExist:
                    return HttpResponseForbidden(
                        "Payment %s does not exist" % payment_id
                    )

                payment.status = OrderPayment.PROCESSED
                payment.currency = currency
                payment.amount = Decimal(float(amount) / SMALLEST_UNIT_FACTOR)
                payment.data = request.POST.copy()
                payment.transaction_id = refno
                payment.payment_method = payment.payment_module

                payment.authorized = now()
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
                    self.order_paid(order, payment=payment)

                return redirect("plata_order_success")

        except Exception as e:
            logger.error("IPN: Processing failure %s" % e)
            raise
