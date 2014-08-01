"""
Payment module for PayPal integration

Needs the following settings to work correctly::

    PAYPAL = {
        'BUSINESS': 'yourbusiness@paypal.com',
        'LIVE': True, # Or False
        }
"""

from __future__ import absolute_import, unicode_literals

from decimal import Decimal
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils import six
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt

import plata
from plata.payment.modules.base import ProcessorBase
from plata.shop.models import OrderPayment


logger = logging.getLogger('plata.payment.paypal')

csrf_exempt_m = method_decorator(csrf_exempt)


def urlopen(*args, **kwargs):
    return six.moves.urllib.urlopen(*args, **kwargs)


class PaymentProcessor(ProcessorBase):
    key = 'paypal'
    default_name = _('Paypal')

    def get_urls(self):
        from django.conf.urls import patterns, url

        return patterns(
            '',
            url(r'^payment/paypal/ipn/$', self.ipn,
                name='plata_payment_paypal_ipn'),
        )

    def process_order_confirmed(self, request, order):
        PAYPAL = settings.PAYPAL

        if not order.balance_remaining:
            return self.already_paid(order)

        logger.info('Processing order %s using Paypal' % order)

        payment = self.create_pending_payment(order)
        if plata.settings.PLATA_STOCK_TRACKING:
            StockTransaction = plata.stock_model()
            self.create_transactions(
                order, _('payment process reservation'),
                type=StockTransaction.PAYMENT_PROCESS_RESERVATION,
                negative=True, payment=payment)

        if PAYPAL['LIVE']:
            PP_URL = "https://www.paypal.com/cgi-bin/webscr"
        else:
            PP_URL = "https://www.sandbox.paypal.com/cgi-bin/webscr"

        return self.shop.render(request, 'payment/%s_form.html' % self.key, {
            'order': order,
            'payment': payment,
            'RETURN_SCHEME': PAYPAL.get(
                'RETURN_SCHEME',
                'https' if request.is_secure() else 'http'
            ),
            'IPN_SCHEME': PAYPAL.get('IPN_SCHEME', 'http'),
            'HTTP_HOST': request.META.get('HTTP_HOST'),
            'post_url': PP_URL,
            'business': PAYPAL['BUSINESS'],
        })

    @csrf_exempt_m
    def ipn(self, request):
        if not request._read_started:
            if 'windows-1252' in request.body.decode('windows-1252', 'ignore'):
                if request.encoding != 'windows-1252':
                    request.encoding = 'windows-1252'
        else:  # middleware (or something else?) has triggered request reading
            if request.POST.get('charset') == 'windows-1252':
                if request.encoding != 'windows-1252':
                    # since the POST data has already been accessed,
                    # unicode characters may have already been lost and
                    # cannot be re-encoded.
                    # -- see https://code.djangoproject.com/ticket/14035
                    # Unfortunately, PayPal:
                    # a) defaults to windows-1252 encoding (why?!)
                    # b) doesn't indicate this in the Content-Type header
                    #    so Django cannot automatically detect it.
                    logger.warning(
                        'IPN received with charset=windows1252, however '
                        'the request encoding does not match. It may be '
                        'impossible to verify this IPN if the data contains '
                        'non-ASCII characters. Please either '
                        'a) update your PayPal preferences to use UTF-8 '
                        'b) configure your site so that IPN requests are '
                        'not ready before they reach the hanlder'
                    )

        PAYPAL = settings.PAYPAL

        if PAYPAL['LIVE']:
            PP_URL = "https://www.paypal.com/cgi-bin/webscr"
        else:
            PP_URL = "https://www.sandbox.paypal.com/cgi-bin/webscr"

        parameters = None

        try:
            parameters = request.POST.copy()
            parameters_repr = repr(parameters).encode('utf-8')

            if parameters:
                logger.info(
                    'IPN: Processing request data %s' % parameters_repr)

                querystring = 'cmd=_notify-validate&%s' % (
                    request.POST.urlencode()
                )
                status = urlopen(PP_URL, querystring).read()

                if not status == "VERIFIED":
                    logger.error(
                        'IPN: Received status %s, '
                        'could not verify parameters %s' % (
                            status,
                            parameters_repr
                        )
                    )
                    logger.debug('Destination: %r ? %r', PP_URL, querystring)
                    logger.debug('Request: %r', request)
                    return HttpResponseForbidden('Unable to verify')

            if parameters:
                logger.info('IPN: Verified request %s' % parameters_repr)
                reference = parameters['txn_id']
                invoice_id = parameters['invoice']
                currency = parameters['mc_currency']
                amount = parameters['mc_gross']

                try:
                    order, order_id, payment_id = invoice_id.split('-')
                except ValueError:
                    logger.error(
                        'IPN: Error getting order for %s' % invoice_id)
                    return HttpResponseForbidden('Malformed order ID')

                try:
                    order = self.shop.order_model.objects.get(pk=order_id)
                except (self.shop.order_model.DoesNotExist, ValueError):
                    logger.error('IPN: Order %s does not exist' % order_id)
                    return HttpResponseForbidden(
                        'Order %s does not exist' % order_id)

                try:
                    payment = order.payments.get(pk=payment_id)
                except (order.payments.model.DoesNotExist, ValueError):
                    payment = order.payments.model(
                        order=order,
                        payment_module=u'%s' % self.name,
                    )

                payment.status = OrderPayment.PROCESSED
                payment.currency = currency
                payment.amount = Decimal(amount)
                payment.data = request.POST.copy()
                payment.transaction_id = reference
                payment.payment_method = payment.payment_module

                if parameters['payment_status'] == 'Completed':
                    payment.authorized = timezone.now()
                    payment.status = OrderPayment.AUTHORIZED

                payment.save()
                order = order.reload()

                logger.info(
                    'IPN: Successfully processed IPN request for %s' % order)

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

                return HttpResponse("Ok")

        except Exception as e:
            logger.error('IPN: Processing failure %s' % e)
            raise
        else:
            logger.warning('IPN received without POST parameters')
            return HttpResponseForbidden('No parameters provided')
