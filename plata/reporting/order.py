from decimal import Decimal

from django.core.urlresolvers import get_callable
from django.utils.text import capfirst
from django.utils.translation import ugettext as _

from pdfdocument.document import cm, mm
from pdfdocument.elements import create_stationery_fn

import plata


class OrderReport(object):
    def __init__(self, pdf, order):
        self.pdf = pdf
        self.order = order

    def init_letter(self):
        self.pdf.init_letter(page_fn=create_stationery_fn(
            get_callable(plata.settings.PLATA_REPORTING_STATIONERY)()))

    def address(self, address_key):
        """
        ``address_key`` must be one of ``shipping`` and ``billing``.
        """

        if plata.settings.PLATA_REPORTING_ADDRESSLINE:
            self.pdf.address_head(plata.settings.PLATA_REPORTING_ADDRESSLINE)

        self.pdf.address(self.order.addresses()[address_key])
        self.pdf.next_frame()

    def title(self):
        self.pdf.p(u'%s: %s' % (
            capfirst(_('order date')),
            self.order.confirmed and self.order.confirmed.strftime('%d.%m.%Y') or _('Not confirmed yet'),
            ))
        self.pdf.spacer(3*mm)

        self.pdf.h1(_('Order %s') % self.order.order_id)
        self.pdf.hr()

    def items_without_prices(self):
        self.pdf.table([(
                _('SKU'),
                capfirst(_('product')),
                capfirst(_('quantity')),
            )]+[
            (
                item.sku,
                item.name,
                item.quantity,
            ) for item in self.order.items.all()],
            (2*cm, 13.4*cm, 1*cm), self.pdf.style.tableHead+(
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ))

    def items_with_prices(self):
        self.pdf.table([(
                _('SKU'),
                capfirst(_('product')),
                capfirst(_('quantity')),
                capfirst(_('unit price')),
                capfirst(_('line item price')),
            )]+[
            (
                item.sku,
                item.name,
                item.quantity,
                u'%.2f' % item.unit_price,
                u'%.2f' % item.discounted_subtotal,
            ) for item in self.order.items.all()],
            (2*cm, 6*cm, 1*cm, 3*cm, 4.4*cm), self.pdf.style.tableHead+(
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ))

    def summary(self):
        summary_table = [
            ('', ''),
            (capfirst(_('subtotal')), u'%.2f' % self.order.subtotal),
            ]

        if self.order.discount:
            summary_table.append((capfirst(_('discount')), u'%.2f' % self.order.discount))

        if self.order.shipping:
            summary_table.append((capfirst(_('shipping')), u'%.2f' % self.order.shipping))

        self.pdf.table(summary_table, (12*cm, 4.4*cm), self.pdf.style.table)

        self.pdf.spacer(1*mm)

        total_title = u'%s %s' % (capfirst(_('total')), self.order.currency)

        if self.order.tax:
            if 'tax_details' in self.order.data:
                zero = Decimal('0.00')

                self.pdf.table([(
                    u'',
                    u'%s %s' % (
                        _('Incl. tax'),
                        u'%.1f%%' % row['tax_rate'],
                        ),
                    row['total'].quantize(zero),
                    row['tax_amount'].quantize(zero),
                    u'',
                    ) for rate, row in self.order.data['tax_details']],
                    (2*cm, 4*cm, 3*cm, 3*cm, 4.4*cm), self.pdf.style.table)

        self.pdf.table([
            (total_title, u'%.2f' % self.order.total),
            ], (12*cm, 4.4*cm), self.pdf.style.tableHead)

        self.pdf.spacer()
        if self.order.is_paid:
            try:
                payment = self.order.payments.authorized()[0]
            except IndexError:
                payment = None

            if payment:
                self.pdf.p(_('Already paid for with %(payment_method)s (Transaction %(transaction)s).') % {
                    'payment_method': payment.payment_method,
                    'transaction': payment.transaction_id,
                    })
            else:
                self.pdf.p(_('Already paid for.'))
        else:
            self.pdf.p(_('Not paid yet.'))

    def notes(self):
        if self.order.notes:
            self.pdf.spacer(10*mm)
            self.pdf.p(capfirst(_('notes')), style=self.pdf.style.bold)
            self.pdf.spacer(1*mm)
            self.pdf.p(self.order.notes)


def invoice_pdf(pdf, order):
    """PDF suitable for use as invoice"""

    report = OrderReport(pdf, order)
    report.init_letter()
    report.address('billing')
    report.title()
    report.items_with_prices()
    report.summary()

    pdf.generate()


def packing_slip_pdf(pdf, order):
    """PDF suitable for use as packing slip"""

    report = OrderReport(pdf, order)
    report.init_letter()
    report.address('shipping')
    report.title()
    report.items_without_prices()
    report.notes()

    pdf.generate()
