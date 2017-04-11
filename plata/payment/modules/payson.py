# -*- coding: utf-8 -*-
# Plata payment module wrapper for Payson
import logging
from decimal import Decimal
from django import http
from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

import plata
import plata.shop.models
from plata.payment.modules.base import ProcessorBase
import payson_api


csrf_exempt_m = method_decorator(csrf_exempt)
require_POST_m = method_decorator(require_POST)
require_GET_m = method_decorator(require_GET)


logger = logging.getLogger('django')


class PaymentProcessor(ProcessorBase):
    key = 'payson'
    default_name = _(u'Payson')

    def __init__(self, shop):
        super(PaymentProcessor, self).__init__(shop)
        self.payson_api = payson_api.PaysonApi(
            settings.PAYSON['USER_ID'],
            settings.PAYSON['USER_KEY'])

    def get_urls(self):
        from django.conf.urls import url
        return [
            url(r'^payment/payson/ipn/$', self.ipn,
                name='payson_ipn'),
            url(r'^payment/payson/return/$', self.return_url,
                name='payson_return'),
        ]

    def process_order_confirmed(self, request, order):
        if not order.balance_remaining:
            return self.already_paid(order)
        if order.currency not in ('SEK', 'EUR'):
            raise ValueError('Payson payments only support SEK and EUR, not %s.' % order.currency)

        # TODO: log
        payment = self.create_pending_payment(order)
        self.reserve_stock_item(order, payment)
        locale_code = (order.language_code or settings.LANGUAGE_CODE).upper()[:2]
        if locale_code not in ('SV', 'FI', 'EN'):
            locale_code = 'EN'
        pay_response = self.payson_api.pay(
            returnUrl=request.build_absolute_uri(reverse('payson_return')),
            cancelUrl=request.build_absolute_uri(reverse('shop_checkout')),
            memo=', '.join([item.product.description for item in order.items.all()])[:128],
            senderEmail=order.email,
            senderFirstName=order.billing_first_name,
            senderLastName=order.billing_last_name,
            receiverList=[payson_api.Receiver(settings.PAYSON['EMAIL'], order.total), ],
            ipnNotificationUrl=request.build_absolute_uri(reverse('payson_ipn')),
            localeCode=locale_code,
            currencyCode=order.currency,
            # custom=None,
            trackingId='-'.join((str(order.id), str(payment.id))),
            guaranteeOffered=u'NO',
            orderItemList=(payson_api.OrderItem(
                order_item.name,
                order_item.sku,
                order_item.quantity,
                order_item.product.get_price(orderitem=order_item).unit_price_excl_tax,
                order_item.tax_rate / Decimal(100)) for order_item in order.items.all()),
            showReceiptPage=False
        )
        if pay_response.success:
            # log
            return redirect(pay_response.forward_pay_url)

        else:
            logger.error(', '.join(e.message for e in pay_response.responseEnvelope.errorList))
            return redirect(reverse('plata_order_payment_failure'))

    def update_payment(self, payment_details, request):
        order_id, payment_id = payment_details.trackingId.split('-')
        order = plata.shop.models.Order.objects.select_related('payments').get(pk=order_id)
        if order.status >= plata.shop.models.Order.PAID:
            return order

        payment = order.payments.get(pk=payment_id)
        if payment_details.status not in ('CREATED', 'PENDING', 'PROCESSING'):
            payment.status = plata.shop.models.OrderPayment.PROCESSED
        payment.currency = payment_details.currencyCode
        payment.amount = payment_details.amount
        payment.data = payment_details.post_data
        payment.transaction_id = payment_details.purchaseId
        payment.payment_method = payment_details.type
        payment.transaction_fee = payment_details.receiverFee
        if payment_details.status == 'COMPLETED':
            payment.authorized = timezone.now()
            payment.status = plata.shop.models.OrderPayment.AUTHORIZED
        payment.save()
        order = order.reload()
        if payment.authorized and plata.settings.PLATA_STOCK_TRACKING:
            StockTransaction = plata.stock_model()
            self.create_transactions(
                order,
                _('sale'),
                type=StockTransaction.SALE,
                negative=True,
                payment=payment)
        if not order.balance_remaining:
            self.order_paid(order, payment=payment, request=request)

        return order

    @csrf_exempt_m
    @require_POST_m
    def ipn(self, request):
        try:
            is_valid = self.payson_api.validate(request.body)
        except ValueError:
            # todo log
            return http.HttpResponseBadRequest()
        else:
            if is_valid:
                payment_details = payson_api.PaymentDetails(request.POST)
                self.update_payment(payment_details, request)

        return http.HttpResponse('OK')

    @csrf_exempt_m
    @require_GET_m
    def return_url(self, request):
        token = request.GET.get('TOKEN') or request.GET.get('token')
        payment_details_response = self.payson_api.payment_details(token)
        if payment_details_response.success:
            self.update_payment(payment_details_response, request)
            if payment_details_response.status == 'COMPLETED':
                return redirect(reverse('plata_order_success'))
        return redirect(reverse('plata_order_payment_failure'))
