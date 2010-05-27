import urllib
import urllib2

from django.conf import settings
from django.http import HttpResponse, HttpResponseServerError
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from plata.payment.modules.base import ProcessorBase
from plata.product.stock.models import StockTransaction


csrf_exempt_m = method_decorator(csrf_exempt)


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
            return redirect('plata_order_already_paid')

        payment = order.payments.create(
            currency=order.currency,
            amount=order.balance_remaining,
            payment_module=u'%s' % self.name,
            )

        self.create_transactions(order, _('payment process reservation'),
            type=StockTransaction.PAYMENT_PROCESS_RESERVATION,
            negative=True, payment=payment)

        raise NotImplementedError, 'This is not implemented yet.'

        return render_to_response('payment/paypal_form.html', {
            'order': order,
            'HTTP_HOST': request.META.get('HTTP_HOST'),
            'form_params': form_params,
            }, context_instance=RequestContext(request))


    @method_decorator(csrf_exempt)
    @method_decorator(require_POST)
    def ipn(self, request):
        PAYPAL = settings.PAYPAL

        if PAYPAL['LIVE']:
            PP_URL = "https://www.paypal.com/cgi-bin/webscr"
        else:
            PP_URL = "https://www.sandbox.paypal.com/cgi-bin/webscr"

        parameters = None

        try:
            if request.POST.get('payment_status') == 'Completed':
                if request.POST:
                    parameters = request.POST.copy()
                else:
                    parameters = request.GET.copy()
            else:
                pass
                #log_error("IPN", "The parameter payment_status was not Completed.")

            if parameters:
                parameters['cmd']='_notify-validate'

                params = urllib.urlencode(parameters)
                req = urllib2.Request(PP_URL, params)
                req.add_header("Content-type", "application/x-www-form-urlencoded")
                response = urllib2.urlopen(req)
                status = response.read()
                if not status == "VERIFIED":
                    #print "The request could not be verified, check for fraud." + str(status)
                    parameters = None

            if parameters:
                reference = parameters['txn_id']
                invoice_id = parameters['invoice']
                currency = parameters['mc_currency']
                amount = parameters['mc_gross']
                fee = parameters['mc_fee']
                email = parameters['payer_email']
                identifier = parameters['payer_id']

                # DO SOMETHING WITH THE PARAMETERS HERE, STORE THEM, ETC...

                return HttpResponse("Ok")

        except Exception, e:
            import sys
            sys.stderr.write(unicode(e))
            sys.stderr.flush()

        return HttpResponseServerError()
