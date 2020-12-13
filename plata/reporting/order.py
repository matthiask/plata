from __future__ import absolute_import, unicode_literals

from decimal import Decimal

from django.urls import get_callable
from django.utils.text import capfirst
from django.utils.translation import activate, ugettext as _

import plata
from pdfdocument.document import cm, mm
from pdfdocument.elements import create_stationery_fn


class OrderReport(object):
    def __init__(self, pdf, order):
        self.pdf = pdf
        self.order = order

        if order.language_code:
            activate(order.language_code)

    def init_letter(self):
        self.pdf.init_letter(
            page_fn=create_stationery_fn(
                get_callable(plata.settings.PLATA_REPORTING_STATIONERY)()
            )
        )

    def address(self, address_key):
        """
        ``address_key`` must be one of ``shipping`` and ``billing``.
        """

        if plata.settings.PLATA_REPORTING_ADDRESSLINE:
            self.pdf.address_head(plata.settings.PLATA_REPORTING_ADDRESSLINE)

        self.pdf.address(self.order.addresses()[address_key])
        self.pdf.next_frame()

    def title(self, title=None):
        self.pdf.p(
            "%s: %s"
            % (
                capfirst(_("order date")),
                self.order.confirmed.strftime("%d.%m.%Y")
                if self.order.confirmed
                else _("Not confirmed yet"),
            )
        )
        self.pdf.spacer(3 * mm)

        if not title:
            title = _("Order")
        self.pdf.h1("%s %s" % (title, self.order.order_id))
        self.pdf.hr()

    def items_without_prices(self):
        self.pdf.table(
            [(_("SKU"), capfirst(_("product")), capfirst(_("quantity")))]
            + [(item.sku, item.name, item.quantity) for item in self.order.items.all()],
            (2 * cm, 13.4 * cm, 1 * cm),
            self.pdf.style.tableHead + (("ALIGN", (1, 0), (1, -1), "LEFT"),),
        )

    def items_with_prices(self):
        self.pdf.table(
            [
                (
                    _("SKU"),
                    capfirst(_("product")),
                    capfirst(_("quantity")),
                    capfirst(_("unit price")),
                    capfirst(_("line item price")),
                )
            ]
            + [
                (
                    item.sku,
                    item.name,
                    item.quantity,
                    "%.2f" % item.unit_price,
                    "%.2f" % item.discounted_subtotal,
                )
                for item in self.order.items.all()
            ],
            (2 * cm, 6 * cm, 1 * cm, 3 * cm, 4.4 * cm),
            self.pdf.style.tableHead + (("ALIGN", (1, 0), (1, -1), "LEFT"),),
        )

    def summary(self):
        summary_table = [
            ("", ""),
            (capfirst(_("subtotal")), "%.2f" % self.order.subtotal),
        ]

        if self.order.discount:
            summary_table.append(
                (capfirst(_("discount")), "%.2f" % self.order.discount)
            )

        if self.order.shipping:
            summary_table.append(
                (capfirst(_("shipping")), "%.2f" % self.order.shipping)
            )

        self.pdf.table(summary_table, (12 * cm, 4.4 * cm), self.pdf.style.table)

        self.pdf.spacer(1 * mm)

        total_title = "%s %s" % (capfirst(_("total")), self.order.currency)

        if self.order.tax:
            if "tax_details" in self.order.data:
                zero = Decimal("0.00")

                self.pdf.table(
                    [
                        (
                            "",
                            "%s %s" % (_("Incl. tax"), "%.1f%%" % row["tax_rate"]),
                            row["total"].quantize(zero),
                            row["tax_amount"].quantize(zero),
                            "",
                        )
                        for rate, row in self.order.data["tax_details"]
                        if row["tax_amount"]
                    ],
                    (2 * cm, 4 * cm, 3 * cm, 3 * cm, 4.4 * cm),
                    self.pdf.style.table,
                )

        self.pdf.table(
            [(total_title, "%.2f" % self.order.total)],
            (12 * cm, 4.4 * cm),
            self.pdf.style.tableHead,
        )

        self.pdf.spacer()

    def payment(self):
        if not self.order.balance_remaining:
            try:
                payment = self.order.payments.authorized()[0]
            except IndexError:
                payment = None

            if payment and payment.payment_method:
                self.pdf.p(
                    _("Already paid for with: %(payment_method)s.")
                    % {
                        "payment_method": payment.payment_method
                        + (
                            (
                                " (Transaction %(transaction)s)"
                                % {"transaction": payment.transaction_id}
                            )
                            if payment.transaction_id
                            else ""
                        )
                    }
                )
            else:
                self.pdf.p(_("Already paid for."))
        else:
            self.pdf.p(_("Not paid yet."))

    def notes(self):
        if self.order.notes:
            self.pdf.spacer(10 * mm)
            self.pdf.p(capfirst(_("notes")), style=self.pdf.style.bold)
            self.pdf.spacer(1 * mm)
            self.pdf.p(self.order.notes)

    def address_table(self):
        self.pdf.table(
            [
                (_("Seller"), _("Customer")),
                (plata.settings.PLATA_REPORTING_ADDRESSLINE, self.get_address_data()),
            ],
            (8.2 * cm, 8.2 * cm),
            self.pdf.style.tableBase
            + (
                (
                    "FONT",
                    (0, 0),
                    (-1, 0),
                    "%s-Bold" % self.pdf.style.fontName,
                    self.pdf.style.fontSize,
                ),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("ALIGN", (1, 0), (1, -1), "LEFT"),
            ),
        )
        self.pdf.spacer(10 * mm)
        self.pdf.next_frame()

    def get_address_data(self, prefix=""):
        # overrided so we can just return address as text
        obj = self.order.addresses()["billing"]
        if type(obj) == dict:
            data = obj
        else:
            data = {}
            for field in (
                "company",
                "manner_of_address",
                "first_name",
                "last_name",
                "address",
                "zip_code",
                "city",
                "full_override",
            ):
                attribute = "%s%s" % (prefix, field)
                data[field] = getattr(obj, attribute, "").strip()

        address = []
        if data.get("company", False):
            address.append(data["company"])

        title = data.get("manner_of_address", "")
        if title:
            title += " "

        if data.get("first_name", False):
            address.append(
                "%s%s %s"
                % (title, data.get("first_name", ""), data.get("last_name", ""))
            )
        else:
            address.append("%s%s" % (title, data.get("last_name", "")))

        address.append(data.get("address"))
        address.append("%s %s" % (data.get("zip_code", ""), data.get("city", "")))

        if data.get("full_override"):
            address = [
                line.strip()
                for line in data.get("full_override").replace("\r", "").splitlines()
            ]

        return "\n".join(address)


def invoice_pdf(pdf, order):
    """PDF suitable for use as invoice"""

    report = OrderReport(pdf, order)
    report.init_letter()
    report.address_table()
    report.title()
    report.items_with_prices()
    report.summary()
    report.payment()

    pdf.generate()


def packing_slip_pdf(pdf, order):
    """PDF suitable for use as packing slip"""

    report = OrderReport(pdf, order)
    report.init_letter()
    report.address("shipping")
    report.title()
    report.items_without_prices()
    report.notes()

    pdf.generate()
