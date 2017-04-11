# -*- coding: utf-8 -*-
import hashlib
import json
import logging
import decimal
from django import http

from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

import billogram_api

import plata.shop.models
from plata.payment.modules.base import ProcessorBase

logger = logging.getLogger('django')

csrf_exempt_m = method_decorator(csrf_exempt)
require_POST_m = method_decorator(require_POST)

CUSTOMER_NO_OFFSET = 10000


class PaymentProcessor(ProcessorBase):
    key = 'billogram'
    default_name = _('invoice')

    def __init__(self, *args, **kwargs):
        super(PaymentProcessor, self).__init__(*args, **kwargs)
        self.api = billogram_api.BillogramAPI(
            settings.BILLOGRAM['API_USER'],
            settings.BILLOGRAM['API_AUTHKEY'],
            api_base=settings.BILLOGRAM['API_BASE']
        )

    def get_urls(self):
        from django.conf.urls import url
        return [
            url(r'^payment/billogram/$',
                self.callback,
                name='billogram_callback')
        ]

    def get_or_create_customer(self, order):
        customer_no = order.user_id + CUSTOMER_NO_OFFSET
        try:
            return self.api.customers.get(customer_no)

        except billogram_api.BillogramExceptions.ObjectNotFoundError:
            name = ' '.join((order.billing_first_name,
                             order.billing_last_name))
            address = all((name, order.billing_address, order.billing_city,
                           order.billing_zip_code, order.billing_country.code))
            delivery_address = all((order.shipping_first_name,
                                    order.shipping_last_name,
                                    order.shipping_address,
                                    order.shipping_city,
                                    order.shipping_zip_code,
                                    order.shipping_country.code))
            customer_data = {
                "customer_no": customer_no,
                "name": name,
                "contact": {
                    "name": name,
                    "email": order.email,
                },
                "company_type": "%sindividual" % (
                    'foreign ' if order.billing_country.code != 'SE' else ''),
            }
            if address:
                billing_address = order.billing_address.split('\n', 1)
                if len(billing_address) > 1:
                    careof, street_address = billing_address
                    # TODO: strip any c/o from careof, it will be doubled
                else:
                    careof, street_address = '', billing_address[0]
                customer_data['address'] = {
                    "street_address": street_address,
                    "careof": careof,
                    "city": order.billing_city,
                    "zipcode": order.billing_zip_code,
                    "country": order.billing_country.code,
                }

            if delivery_address:
                customer_data["delivery_address"] = {
                    "name": "%s %s" % (order.shipping_first_name,
                                       order.shipping_last_name),
                    "street_address": order.shipping_address,  # todo split this too
                    "city": order.shipping_city,
                    "zipcode": order.shipping_zip_code,
                    "country": order.shipping_country.code,
                }
            return self.api.customers.create(customer_data)

    def process_order_confirmed(self, request, order):
        if not order.balance_remaining:
            return self.already_paid(order)
        payment = self.create_pending_payment(order)
        self.reserve_stock_item(order, payment)
        customer = self.get_or_create_customer(order)
        billogram_data = {
            "customer": {
                "customer_no": customer['customer_no'],
            },
            "items": [{
                "count": item.quantity,
                "title": item.name[:40],
                "unit": "unit",
                "price": str(item.product.get_price(orderitem=item).unit_price_excl_tax),
                "vat": int(item.tax_rate),
            } for item in order.items.all()],
            "invoice_fee": str(order.shipping_cost),  # TODO: use a real invoice fee field
        }
        if 'localhost' not in request.get_host():  # Billogram does not allow localhost to be sent in
            billogram_data["callbacks"] = {
                "url": request.build_absolute_uri(reverse('billogram_callback')),
                "custom": '-'.join((str(order.id), str(payment.id))),
                "sign_key": settings.BILLOGRAM['SIGN_KEY'],
            }

        methods = []
        if customer.data.get('contact', {}).get('email'):
            methods.append('Email')
        if customer.data.get('address'):
            methods.append('Letter')
        method = '+'.join(methods)

        try:
            billogram = self.api.billogram.create_and_send(billogram_data, method)
            payment.transaction_id = billogram.id
            payment.save()
            order.shipping_tax_rate = billogram.invoice_fee_vat
            order.recalculate_total(save=True)
        except Exception, e:
            logger.error(str(e))
            # message error
            return redirect(reverse('plata_order_payment_failure'))
        else:
            # set as authorized?
            # subtract from stock
            # message success
            return redirect(reverse('plata_order_payment_pending'))

    @csrf_exempt_m
    @require_POST_m
    def callback(self, request):
        data = json.loads(request.body)
        if data['signature'] != hashlib.md5(
                data['callback_id'] +
                settings.BILLOGRAM['SIGN_KEY']).hexdigest():
            return http.HttpResponseBadRequest()

        order_id, payment_id = data['custom'].split('-')
        order = plata.shop.models.Order.objects.get(pk=order_id)
        if order.status >= plata.shop.models.Order.PAID:
            return http.HttpResponse('OK')

        payment = order.payments.get(pk=payment_id)
        payment.data.setdefault('cb_data_list', []).append(data)  # plata JSONField needs dict as root obj,,,
        event_type = data['event']['type']
        if event_type == 'Payment':
            amount = decimal.Decimal(data['event']['data']['amount'])
            payment.amount = amount
            try:
                payment.transaction_fee = amount - decimal.Decimal(
                    data['event']['data']['banking_amount']
                )
            except TypeError:
                pass
#  payment.status
#  payment.payment_method = payment_details.type

        elif event_type == 'CustomerMessage':
            payment.notes = data['event']['data']['message']
        elif event_type == 'BillogramEnded' and data['billogram']['state'] == 'Paid':
            payment.authorized = timezone.now()
            payment.status = plata.shop.models.OrderPayment.AUTHORIZED
        # TODO: release stock if cancelled or credited
        payment.save()
        order = order.reload()
        if not order.balance_remaining:
            self.order_paid(order, payment=payment, request=request)

        return http.HttpResponse('OK')
