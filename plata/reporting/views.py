from decimal import Decimal
import StringIO

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from pdfdocument.utils import pdf_response

import plata
import plata.reporting.product
import plata.reporting.order


@staff_member_required
def product_xls(request):
    output = StringIO.StringIO()
    workbook = plata.reporting.product.product_xls()
    workbook.save(output)
    response = HttpResponse(output.getvalue(), mimetype='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=products.xls'
    return response


@staff_member_required
def order_pdf(request, order_id):
    order = get_object_or_404(plata.shop_instance().order_model, pk=order_id)

    pdf, response = pdf_response('order-%09d' % order.id)
    plata.reporting.order.order_pdf(pdf, order)
    return response
