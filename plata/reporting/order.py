from django.utils.text import capfirst
from django.utils.translation import ugettext as _

from pdfdocument.document import PDFDocument, cm, mm
from pdfdocument.elements import create_stationery_fn, ExampleStationery
from pdfdocument.utils import pdf_response


def order_pdf(pdf, order):
    pdf.init_letter(page_fn=create_stationery_fn(ExampleStationery()))

    pdf.address_head(u'FEINHEIT GmbH - Molkenstrasse 21 - CH-8004 Z\374rich')
    pdf.address(order, 'billing_')
    pdf.next_frame()

    pdf.p(u'%s: %s' % (
        capfirst(_('order date')),
        order.confirmed and order.confirmed.strftime('%d.%m.%Y') or _('Not confirmed yet'),
        ))
    pdf.spacer(3*mm)

    pdf.h1('Order %09d' % order.id)
    pdf.hr()

    pdf.table([(
            capfirst(_('product')),
            capfirst(_('quantity')),
            capfirst(_('unit price')),
            capfirst(_('line item price')),
        )]+[
        (
            unicode(item.variation),
            item.quantity,
            u'%.2f' % item.unit_price,
            u'%.2f' % item.discounted_subtotal,
        ) for item in order.items.all()],
        (8*cm, 1*cm, 3*cm, 4.4*cm), pdf.style.tableHead)

    summary_table = [
        ('', ''),
        (capfirst(_('subtotal')), u'%.2f' % order.subtotal),
        ]

    if order.discount:
        summary_table.append((capfirst(_('discount')), u'%.2f' % order.discount))

    if order.shipping:
        summary_table.append((capfirst(_('shipping')), u'%.2f' % order.shipping))

    pdf.table(summary_table, (12*cm, 4.4*cm), pdf.style.table)

    pdf.spacer(1*mm)
    pdf.table([
        (u'%s %s' % (capfirst(_('total')), order.currency), u'%.2f' % order.total),
        ], (12*cm, 4.4*cm), pdf.style.tableHead)

    pdf.generate()

