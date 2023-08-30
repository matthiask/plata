from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404
from pdfdocument.utils import pdf_response

import plata.reporting.order

# import plata
import plata.reporting.product
from plata.reporting.pdfdocument import PlataPDFDocument


@staff_member_required
def product_xls(request):
    """
    Returns an XLS containing product information
    """
    return plata.reporting.product.product_xls().to_response("products.xlsx")


@staff_member_required
def invoice_pdf(request, order_id):
    """
    Returns the invoice PDF
    """
    order = get_object_or_404(plata.shop_instance().order_model, pk=order_id)

    pdf, response = pdf_response(
        "invoice-%09d" % order.id, pdfdocument=PlataPDFDocument
    )
    plata.reporting.order.invoice_pdf(pdf, order)
    return response


@login_required
def invoice(request, order_id):
    """
    Returns the invoice PDF
    """
    order = get_object_or_404(plata.shop_instance().order_model, pk=order_id)

    if order in request.user.orders.all():
        pdf, response = pdf_response("invoice-%09d" % order.id)
        plata.reporting.order.invoice_pdf(pdf, order)
        return response
    else:
        raise Http404


@staff_member_required
def packing_slip_pdf(request, order_id):
    """
    Returns the packing slip PDF
    """
    order = get_object_or_404(plata.shop_instance().order_model, pk=order_id)

    pdf, response = pdf_response(
        "packing-slip-%09d" % order.id, pdfdocument=PlataPDFDocument
    )
    plata.reporting.order.packing_slip_pdf(pdf, order)
    return response
