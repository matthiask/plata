from datetime import datetime
from decimal import Decimal
import urllib
import sys, traceback

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden,\
    HttpResponseServerError
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _

from plata.payment.modules.base import ProcessorBase
from plata.product.stock.models import StockTransaction
from plata.shop.models import OrderPayment


class PaymentProcessor(ProcessorBase):
    name = _('Paypal')

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url

        return patterns('',
            url(r'^payment/paypal/ipn/$', self.ipn, name='plata_payment_paypal_ipn'),
            )

    def process_order_confirmed(self, request, order):
        PAYPAL = settings.PAYPAL

        if order.is_paid():
            # TODO maybe create stock transactions?
            return redirect('plata_order_already_paid')

        payment = self.create_pending_payment(order)

        self.create_transactions(order, _('payment process reservation'),
            type=StockTransaction.PAYMENT_PROCESS_RESERVATION,
            negative=True, payment=payment)

        if PAYPAL['LIVE']:
            PP_URL = "https://www.paypal.com/cgi-bin/webscr"
        else:
            PP_URL = "https://www.sandbox.paypal.com/cgi-bin/webscr"

        return render_to_response('payment/paypal_form.html', {
            'order': order,
            'payment': payment,
            'HTTP_HOST': request.META.get('HTTP_HOST'),
            'post_url': PP_URL,
            'business': PAYPAL['BUSINESS'],
            }, context_instance=RequestContext(request))

    @method_decorator(csrf_exempt)
    @method_decorator(require_POST)
    def ipn(self, request):
        request.encoding = 'windows-1252'
        PAYPAL = settings.PAYPAL

        if PAYPAL['LIVE']:
            PP_URL = "https://www.paypal.com/cgi-bin/webscr"
        else:
            PP_URL = "https://www.sandbox.paypal.com/cgi-bin/webscr"

        parameters = None

        sys.stderr.write('stage 1');sys.stderr.flush()

        try:
            parameters = request.POST.copy()
            sys.stderr.write('stage 2');sys.stderr.flush()

            if parameters:
                sys.stderr.write(repr(parameters).encode('utf-8'))
                sys.stderr.flush()

                postparams = {'cmd': '_notify-validate'}
                for k, v in parameters.iteritems():
                    postparams[k] = v.encode('windows-1252')
                status = urllib.urlopen(PP_URL, urllib.urlencode(postparams)).read()

                sys.stderr.write('STATUS %r' % status)
                if not status == "VERIFIED":
                    #print "The request could not be verified, check for fraud." + str(status)
                    parameters = None

            sys.stderr.write('stage 4');sys.stderr.flush()

            if parameters:
                reference = parameters['txn_id']
                invoice_id = parameters['invoice']
                currency = parameters['mc_currency']
                amount = parameters['mc_gross']

                sys.stderr.write('stage 5');sys.stderr.flush()

                try:
                    order, order_id, payment_id = invoice_id.split('-')
                except ValueError:
                    return HttpResponseForbidden('Malformed order ID')

                sys.stderr.write('stage 6');sys.stderr.flush()

                order = get_object_or_404(self.shop.order_model, pk=order_id)
                try:
                    payment = order.payments.get(pk=payment_id)
                except order.payments.model.DoesNotExist:
                    payment = order.payments.model(
                        order=order,
                        payment_module=u'%s' % self.name,
                        )

                sys.stderr.write('stage 7');sys.stderr.flush()
                payment.status = OrderPayment.PROCESSED
                payment.currency = currency
                payment.amount = Decimal(amount)
                payment.data = request.POST.copy()
                payment.transaction_id = reference
                #payment.payment_method = BRAND
                #payment.notes = STATUS_DICT.get(STATUS)

                if parameters['payment_status'] == 'Completed':
                    payment.authorized = datetime.now()
                    payment.status = OrderPayment.AUTHORIZED

                payment.save()

                if payment.authorized:
                    self.create_transactions(order, _('sale'),
                        type=StockTransaction.SALE, negative=True, payment=payment)

                order = order.reload()
                if order.is_paid():
                    self.order_completed(order)

                return HttpResponse("Ok")

        except Exception, e:
            sys.stderr.flush('PLATA PAYPAL EXCEPTION\n%s\n' % unicode(e))
            traceback.print_exc(100, sys.stderr)
            sys.stderr.flush()
            raise
    ipn.csrf_exempt = True
