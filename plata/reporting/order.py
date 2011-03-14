from decimal import Decimal

from django.core.urlresolvers import get_callable
from django.utils.text import capfirst
from django.utils.translation import ugettext as _

from pdfdocument.document import PDFDocument, cm, mm
from pdfdocument.elements import create_stationery_fn, ExampleStationery
from pdfdocument.utils import pdf_response

import plata


def invoice_pdf(pdf, order):
    """PDF suitable for use as invoice"""

    pdf.init_letter(page_fn=create_stationery_fn(
        get_callable(plata.settings.PLATA_REPORTING_STATIONERY)()))

    if plata.settings.PLATA_REPORTING_ADDRESSLINE:
        pdf.address_head(plata.settings.PLATA_REPORTING_ADDRESSLINE)

    pdf.address(order, 'billing_')
    pdf.next_frame()

    pdf.p(u'%s: %s' % (
        capfirst(_('order date')),
        order.confirmed and order.confirmed.strftime('%d.%m.%Y') or _('Not confirmed yet'),
        ))
    pdf.spacer(3*mm)

    pdf.h1(_('Order %09d') % order.id)
    pdf.hr()

    pdf.table([(
            _('SKU'),
            capfirst(_('product')),
            capfirst(_('quantity')),
            capfirst(_('unit price')),
            capfirst(_('line item price')),
        )]+[
        (
            item.variation.sku,
            unicode(item.variation),
            item.quantity,
            u'%.2f' % item.unit_price,
            u'%.2f' % item.discounted_subtotal,
        ) for item in order.items.all()],
        (2*cm, 6*cm, 1*cm, 3*cm, 4.4*cm), pdf.style.tableHead+(
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ))

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

    total_title = u'%s %s' % (capfirst(_('total')), order.currency)

    if order.tax:
        if 'tax_details' in order.data:
            zero = Decimal('0.00')

            pdf.table([(
                u'',
                u'%s %s' % (
                    _('Incl. tax'),
                    u'%.1f%%' % row['tax_rate'],
                    ),
                row['total'].quantize(zero),
                row['tax_amount'].quantize(zero),
                u'',
                ) for rate, row in order.data['tax_details']],
                (2*cm, 4*cm, 3*cm, 3*cm, 4.4*cm), pdf.style.table)

    pdf.table([
        (total_title, u'%.2f' % order.total),
        ], (12*cm, 4.4*cm), pdf.style.tableHead)

    pdf.spacer()
    if order.is_paid:
        try:
            payment = order.payments.authorized()[0]
        except IndexError:
            payment = None

        if payment:
            pdf.p(_('Already paid for with %(payment_method)s (Transaction %(transaction)s).') % {
                'payment_method': payment.payment_method,
                'transaction': payment.transaction_id,
                })
        else:
            pdf.p(_('Already paid for.'))
    else:
        pdf.p(_('Not paid yet.'))

    pdf.generate()


def packing_slip_pdf(pdf, order):
    """PDF suitable for use as packing slip"""

    pdf.init_letter(page_fn=create_stationery_fn(
        get_callable(plata.settings.PLATA_REPORTING_STATIONERY)()))

    if plata.settings.PLATA_REPORTING_ADDRESSLINE:
        pdf.address_head(plata.settings.PLATA_REPORTING_ADDRESSLINE)

    pdf.address(order.addresses()['shipping'])
    pdf.next_frame()

    pdf.p(u'%s: %s' % (
        capfirst(_('order date')),
        order.confirmed and order.confirmed.strftime('%d.%m.%Y') or _('Not confirmed yet'),
        ))
    pdf.spacer(3*mm)

    pdf.h1(_('Order %09d') % order.id)
    pdf.hr()

    pdf.table([(
            _('SKU'),
            capfirst(_('product')),
            capfirst(_('quantity')),
        )]+[
        (
            item.variation.sku,
            unicode(item.variation),
            item.quantity,
        ) for item in order.items.all()],
        (2*cm, 13.4*cm, 1*cm), pdf.style.tableHead+(
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ))

    if order.notes:
        pdf.spacer(10*mm)
        pdf.p(capfirst(_('notes')), style=pdf.style.bold)
        pdf.spacer(1*mm)
        pdf.p(order.notes)

    pdf.generate()

