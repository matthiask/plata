from decimal import Decimal

from django.shortcuts import get_object_or_404

from pdfdocument.utils import pdf_response

import plata
import plata.reporting.order


def order_pdf(request, order_id):
    order = get_object_or_404(plata.shop_instance().order_model, pk=order_id)

    order.shipping_cost = 8 / Decimal('1.076')
    order.shipping_discount = 0
    order.recalculate_total(save=False)

    pdf, response = pdf_response('order-%09d' % order.id)
    plata.reporting.order.order_pdf(pdf, order)
    return response
