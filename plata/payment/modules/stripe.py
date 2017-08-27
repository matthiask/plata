# -*- coding: utf-8 -*-
"""
Payment module for Stripe.com

2017 by fiëé visuëlle, Henning Hraban Ramm

Configuration::

    STRIPE = {
        'PUBLIC_KEY': 'pk_test_#####',
        'SECRET_KEY': 'sk_test_#####',
        'LOGO': '%simg/mylogo.png' % STATIC_URL,
        'template': 'plata/payment/stripe_form.html',
        }

"""
from __future__ import unicode_literals
from __future__ import absolute_import
import logging
import json
from django.conf import settings
from django.conf.urls import url
from django.contrib.sites.shortcuts import get_current_site
from django.utils.translation import ugettext_lazy as _
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
import plata
from plata.payment.modules.base import ProcessorBase
from plata.shop.models import OrderPayment
import stripe  # official API, see https://stripe.com/docs/api/python

logger = logging.getLogger('plata.payment.stripe')
csrf_exempt_m = method_decorator(csrf_exempt)
require_POST_m = method_decorator(require_POST)

stripe.api_version = '2017-04-06'


def handle_errors(bla):
    try:
        # Use Stripe's library to make requests...
        pass
    except stripe.error.CardError as e:
        # Since it's a decline, stripe.error.CardError will be caught
        body = e.json_body
        err  = body['error']
        logger.error(('Status %s: ' % e.http_status) + 'type "%(type)s", code "%(code)s", param "%(param)s": %(message)s' % err)
    except stripe.error.RateLimitError as e:
        # Too many requests made to the API too quickly
        logger.error('RateLimitError: %s' % e)
    except stripe.error.InvalidRequestError as e:
        # Invalid parameters were supplied to Stripe's API
        logger.error('InvalidRequestError: %s' % e)
    except stripe.error.AuthenticationError as e:
        # Authentication with Stripe's API failed
        # (maybe you changed API keys recently)
        logger.error('AuthenticationError: %s' % e)
    except stripe.error.APIConnectionError as e:
        # Network communication with Stripe failed
        logger.error('APIConnectionError: %s' % e)
    except stripe.error.StripeError as e:
        # Display a very generic error to the user, and maybe send
        # yourself an email
        logger.error('StripeError: %s' % e)
    except Exception as e:
        # Something else happened, completely unrelated to Stripe
        logger.error('Exception: %s' % e)


class PaymentProcessor(ProcessorBase):
    key = 'stripe'
    default_name = _('Stripe')
    template = 'payment/%s_form.html' % key
    amount = 0

    def get_urls(self):
        return [
            url(r'^payment/%s/$' % self.key,
                self.callback,
                name='%s_callback' % self.key)
        ]

    def process_order_confirmed(self, request, order):
        STRIPE = settings.STRIPE
        stripe.api_key = STRIPE['SECRET_KEY']
        if 'template' in STRIPE:
            self.template = STRIPE['template']
        self.amount = 0

        if not order.balance_remaining:
            return self.already_paid(order, request=request)

        logger.info('Processing order %s using %s' % (order, self.default_name))

        payment = self.create_pending_payment(order)
        if plata.settings.PLATA_STOCK_TRACKING:
            StockTransaction = plata.stock_model()
            self.create_transactions(
                order, _('payment process reservation'),
                type=StockTransaction.PAYMENT_PROCESS_RESERVATION,
                negative=True, payment=payment)

        for item in order.items.all():
            itemsum = 0
            if item.unit_price != item.line_item_discount:
                itemsum = item.unit_price
                if item.line_item_discount:
                    itemsum -= item.line_item_discount
            self.amount += itemsum * item.quantity
        self.amount += order.shipping
        if order.currency not in plata.settings.CURRENCIES_WITHOUT_CENTS:
            # only if currency has cents; Stripe takes only integer values
            # keyword zero-decimal currencies
            self.amount = int(self.amount * 100)

        self.order = order

        return self.shop.render(request, self.template, {
            'order': order,
            'payment': payment,
            'post_url': '/payment/%s/' % self.key,  # internal, gets payment token
            'amount': self.amount,
            'currency': order.currency.lower(),
            'public_key': STRIPE['PUBLIC_KEY'],
            'name': get_current_site(request).name,
            'description': _('Order %s') % order,
            'logo': STRIPE['LOGO']
        })

    # @csrf_exempt_m
    @require_POST_m
    def callback(self, request):
        # data = json.loads(request.body)

        customer = stripe.Customer.create(
            email='customer@example.com',
            source=request.form['stripeToken']
        )

        charge = stripe.Charge.create(
            customer=customer.id,
            amount=self.amount,
            currency=self.order.currency.lower(),
            description=_('Order %s') % self.order,
        )

        return self.shop.render(request, self.template, {
            'callback': True,
            'order': self.order,
            'charge': charge,
            'amount': self.amount
        })
