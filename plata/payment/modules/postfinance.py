"""
Payment module for Postfinance integration

Needs the following settings to work correctly::

    POSTFINANCE = {
        'PSPID': 'your_shop_id',
        'LIVE': True, # Or False
        'SHA1_IN': 'yourhash',
        'SHA1_OUT': 'yourotherhash',
        }
"""

from datetime import datetime
from decimal import Decimal
from hashlib import sha1
import locale
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _, get_language, to_locale

from plata.payment.modules.base import ProcessorBase
from plata.product.stock.models import StockTransaction
from plata.shop.models import OrderPayment


logger = logging.getLogger('plata.payment.postfinance')


# Copied from http://e-payment.postfinance.ch/ncol/paymentinfos1.asp
STATUSES = """\
0	Incomplete or invalid
1	Cancelled by client
2	Authorization refused
4	Order stored
41	Waiting client payment
5	Authorized
51	Authorization waiting
52	Authorization not known
55	Stand-by
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

STATUS_DICT = dict(line.split('\t') for line in STATUSES.splitlines())


class PaymentProcessor(ProcessorBase):
    key = 'postfinance'
    default_name = _('Postfinance')

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url

        return patterns('',
            url(r'^payment/postfinance/ipn/$', self.ipn, name='plata_payment_postfinance_ipn'),
            )

    def process_order_confirmed(self, request, order):
        POSTFINANCE = settings.POSTFINANCE

        if order.is_paid():
            return self.already_paid(order)

        logger.info('Processing order %s using Postfinance' % order)

        payment = self.create_pending_payment(order)
        self.create_transactions(order, _('payment process reservation'),
            type=StockTransaction.PAYMENT_PROCESS_RESERVATION,
            negative=True, payment=payment)

        form_params = {
            'orderID': 'Order-%d-%d' % (order.id, payment.id),
            'amount': u'%s' % int(order.balance_remaining.quantize(Decimal('0.00'))*100),
            'currency': order.currency,
            'PSPID': POSTFINANCE['PSPID'],
            'mode': POSTFINANCE['LIVE'] and 'prod' or 'test',
            }

        form_params['SHASign'] = sha1(u''.join((
            form_params['orderID'],
            form_params['amount'],
            form_params['currency'],
            form_params['PSPID'],
            POSTFINANCE['SHA1_IN'],
            ))).hexdigest()

        return render_to_response('payment/postfinance_form.html', {
            'order': order,
            'HTTP_HOST': request.META.get('HTTP_HOST'),
            'form_params': form_params,
            'locale': locale.normalize(to_locale(get_language())).split('.')[0],
            }, context_instance=RequestContext(request))

    def ipn(self, request):
        POSTFINANCE = settings.POSTFINANCE

        try:
            parameters_repr = repr(request.POST.copy()).encode('utf-8')
            logger.info('IPN: Processing request data %s' % parameters_repr)

            try:
                orderID = request.POST['orderID']
                currency = request.POST['currency']
                amount = request.POST['amount']
                PM = request.POST['PM']
                ACCEPTANCE = request.POST['ACCEPTANCE']
                STATUS = request.POST['STATUS']
                CARDNO = request.POST['CARDNO']
                PAYID = request.POST['PAYID']
                NCERROR = request.POST['NCERROR']
                BRAND = request.POST['BRAND']
                SHASIGN = request.POST['SHASIGN']
            except KeyError:
                logger.error('IPN: Missing data in %s' % parameters_repr)
                return HttpResponseForbidden('Missing data')

            sha1_source = u''.join((
                orderID,
                currency,
                amount,
                PM,
                ACCEPTANCE,
                STATUS,
                CARDNO,
                PAYID,
                NCERROR,
                BRAND,
                POSTFINANCE['SHA1_OUT'],
                ))

            sha1_out = sha1(sha1_source).hexdigest()

            if sha1_out.lower() != SHASIGN.lower():
                logger.error('IPN: Invalid hash in %s' % parameters_repr)
                return HttpResponseForbidden('Hash did not validate')

            try:
                order, order_id, payment_id = orderID.split('-')
            except ValueError:
                logger.error('IPN: Error getting order for %s' % orderID)
                return HttpResponseForbidden('Malformed order ID')

            # Try fetching the order and order payment objects
            # We create a new order payment object in case the old one
            # cannot be found.
            try:
                order = self.shop.order_model.objects.get(pk=order_id)
            except self.shop.order_model.DoesNotExist:
                logger.error('IPN: Order %s does not exist' % order_id)
                return HttpResponseForbidden('Order %s does not exist' % order_id)

            try:
                payment = order.payments.get(pk=payment_id)
            except order.payments.model.DoesNotExist:
                payment = order.payments.model(
                    order=order,
                    payment_module=u'%s' % self.name,
                    )

            payment.status = OrderPayment.PROCESSED
            payment.currency = currency
            payment.amount = Decimal(amount)
            payment.data = request.POST.copy()
            payment.transaction_id = PAYID
            payment.payment_method = BRAND
            payment.notes = STATUS_DICT.get(STATUS)

            if STATUS in ('5', '9'):
                payment.authorized = datetime.now()
                payment.status = OrderPayment.AUTHORIZED

            payment.save()
            order = order.reload()

            logger.info('IPN: Successfully processed IPN request for %s' % order)

            if payment.authorized:
                self.create_transactions(order, _('sale'),
                    type=StockTransaction.SALE, negative=True, payment=payment)

            if order.is_paid():
                self.order_completed(order, payment=payment)

            return HttpResponse('OK')
        except Exception, e:
            logger.error('IPN: Processing failure %s' % unicode(e))
            raise
    ipn.csrf_exempt = True
