#-*- coding: utf-8 -*-
"""
Pagseguro payment module for django-plata
Authors: alexandre@mandriva.com.br, jpbraun@mandriva.com
Date: 03/14/2012
"""

from datetime import datetime
from decimal import Decimal
import logging
import urllib
import time
from xml.dom import minidom

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt

from plata.payment.modules.base import ProcessorBase
from plata.shop.models import OrderPayment
import plata

logger = logging.getLogger('plata.payment.pagseguro')

csrf_exempt_m = method_decorator(csrf_exempt)


class PaymentProcessor(ProcessorBase):
    key = 'pagseguro'
    default_name = _('Pagseguro')

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url

        return patterns('',
            url(r'^payment/pagseguro/notify/$', self.psnotify,
                name='plata_payment_pagseguro_notify'),
        )

    def process_order_confirmed(self, request, order):
        PAGSEGURO = settings.PAGSEGURO

        if not order.balance_remaining:
            return self.already_paid(order)

        logger.info('Processing order %s using PagSeguro' % order)

        payment = self.create_pending_payment(order)
        if plata.settings.PLATA_STOCK_TRACKING:
            StockTransaction = plata.stock_model()
            self.create_transactions(order, _('payment process reservation'),
                                     type=StockTransaction.PAYMENT_PROCESS_RESERVATION,
                                     negative=True, payment=payment)

        return self.shop.render(request, 'payment/pagseguro_form.html',
                                {'order': order,
                                 'payment': payment,
                                 'HTTP_HOST': request.META.get('HTTP_HOST'),
                                 'post_url': "https://pagseguro.uol.com.br/v2/checkout/payment.html",
                                 'email': PAGSEGURO['EMAIL']})

    @csrf_exempt_m
    def psnotify(self,request):
        request.encoding = 'ISO-8859-1'
        PAGSEGURO = settings.PAGSEGURO

        data = None

        try:
            data = request.POST.copy()
            data = dict((k, v.encode('ISO-8859-1')) for k, v in data.items())

            if data:
                logger.info("Pagseguro: Processing request data %s" % data)

                if PAGSEGURO.get('LOG'):
                    f = open(PAGSEGURO['LOG'], 'a+')
                    f.write("%s - notification: %s\n" % (time.ctime(), data))
                    f.close()

                notificationCode = data['notificationCode']
                result = urllib.urlopen('https://ws.pagseguro.uol.com.br/v2/transactions/notifications/%s?email=%s&token=%s' %
                                        (notificationCode, PAGSEGURO['EMAIL'], PAGSEGURO['TOKEN'])).read()

                if PAGSEGURO.get('LOG'):
                    f = open(PAGSEGURO['LOG'], 'a')
                    f.write("%s - notification check: %s" % (time.ctime(), result))
                    f.close()

                xml = minidom.parseString(result)
                try:
                    xmlTag = xml.getElementsByTagName('status')[0].toxml()
                    status = xmlTag.replace('<status>','').replace('</status>','')
                    xmlTag = xml.getElementsByTagName('reference')[0].toxml()
                    reference = xmlTag.replace('<reference>','').replace('</reference>','')
                    xmlTag = xml.getElementsByTagName('grossAmount')[0].toxml()
                    amount = xmlTag.replace('<grossAmount>','').replace('</grossAmount>','')
                except (ValueError, IndexError):
                    logger.error("Pagseguro: Can't verify notification: %s" % result.decode('ISO-8859-1'))
                    return HttpResponseForbidden('Order verification failed')

                if PAGSEGURO.get('LOG'):
                    f = open(PAGSEGURO.get('LOG'), 'a')
                    f.write("%s - status: %s, ref: %s, code: %s\n" % (time.ctime(), status, reference, notificationCode))
                    f.close()

                logger.info('Pagseguro: Verified request %s' % result)

                try:
                    order, order_id, payment_id = reference.split('-')
                except ValueError:
                    logger.error('Pagseguro: Error getting order for %s' % reference)
                    return HttpResponseForbidden('Malformed order ID')

                try:
                    order = self.shop.order_model.objects.get(pk=order_id)
                except self.shop.order_model.DoesNotExist:
                    logger.error('Pagseguro: Order %s does not exist' % order_id)
                    return HttpResponseForbidden('Order %s does not exist' % order_id)

                try:
                    payment = order.payments.get(pk=payment_id)
                except order.payments.model.DoesNotExist:
                    payment = order.payments.model(order=order,
                                                   payment_module=u'%s' % self.name)

                payment.status = OrderPayment.PROCESSED
                payment.amount = Decimal(amount)
                payment.data = request.POST.copy()
                payment.transaction_id = notificationCode
                payment.payment_method = payment.payment_module

                if status == '3':
                    payment.authorized = datetime.now()
                    payment.status = OrderPayment.AUTHORIZED
                payment.save()

                order = order.reload()
                payment.amount = Decimal(amount)

                logger.info('Pagseguro: Successfully processed request for %s' % order)

                if payment.authorized and plata.settings.PLATA_STOCK_TRACKING:
                    StockTransaction = plata.stock_model()
                    self.create_transactions(order, _('sale'),
                        type=StockTransaction.SALE, negative=True, payment=payment)

                if not order.balance_remaining:
                    self.order_paid(order, payment=payment)

                return HttpResponse("OK")

        except Exception:
            logger.exception('Pagseguro: Processing failure')
            raise

        return HttpResponseForbidden("Bad request")
