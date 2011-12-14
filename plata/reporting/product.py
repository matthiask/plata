from datetime import date
import xlwt

from django.db.models import Sum
from django.utils.text import capfirst
from django.utils.translation import ugettext as _

import plata
from plata.product.stock.models import Period, StockTransaction
from plata import settings


class Style(object):
    def __init__(self, font_name='Helvetica', font_size=10):
        self.font_normal = xlwt.Font()
        self.font_normal.name = 'Helvetica'
        self.font_normal.bold = False
        self.font_normal.height = 10*0x14

        self.font_bold = xlwt.Font()
        self.font_bold.name = 'Helvetica'
        self.font_bold.bold = True
        self.font_bold.height = 10*0x14

        self.font_big = xlwt.Font()
        self.font_big.name = 'Helvetica'
        self.font_big.bold = False
        self.font_big.height = 12*0x14

        self.font_bigger = xlwt.Font()
        self.font_bigger.name = 'Helvetica'
        self.font_bigger.bold = False
        self.font_bigger.height = 15*0x14

        self.font_title = xlwt.Font()
        self.font_title.name = 'Helvetica'
        self.font_title.bold = True
        self.font_title.height = 15*0x14

        self.font_subtitle = xlwt.Font()
        self.font_subtitle.name = 'Helvetica'
        self.font_subtitle.bold = True
        self.font_subtitle.height = 13*0x14

        self.alignment_right = xlwt.Alignment()
        self.alignment_right.horz = xlwt.Alignment.HORZ_RIGHT

        self.normal = xlwt.XFStyle()
        self.normal.font = self.font_normal

        self.bold = xlwt.XFStyle()
        self.bold.font = self.font_bold

        self.subtitle = xlwt.XFStyle()
        self.subtitle.font = self.font_subtitle
        self.subtitle.alignment = self.alignment_right

        self.big = xlwt.XFStyle()
        self.big.font = self.font_big

        self.bigger = xlwt.XFStyle()
        self.bigger.font = self.font_bigger

        self.title = xlwt.XFStyle()
        self.title.font = self.font_title

        self.right = xlwt.XFStyle()
        self.right.font = self.font_normal
        self.right.alignment = self.alignment_right


def product_xls():
    """
    Create a list of all product variations, including stock and aggregated
    stock transactions (by type)
    """

    workbook = xlwt.Workbook()
    s = workbook.add_sheet(capfirst(_('products')))

    style = Style()

    row = 0
    s.write(row, 0, capfirst(_('products')), style=style.title)

    row += 1
    s.write(row, 0, _('Report of %s') % (date.today().strftime('%Y-%m-%d')), style=style.normal)

    row += 2
    s.write(row, 0, capfirst(_('product')), style=style.bold)
    s.write(row, 1, _('SKU'), style=style.bold)
    s.write(row, 2, capfirst(_('stock')), style=style.bold)

    col = 10
    for type_id, type_name in StockTransaction.TYPE_CHOICES:
        s.write(row, col, unicode(type_name), style=style.bold)
        col += 1

    row += 2

    s.col(0).width = 10000
    s.col(1).width = 3000
    s.col(2).width = 2000
    s.col(3).width = 300
    s.col(4).width = 300
    s.col(5).width = 300
    s.col(6).width = 300
    s.col(7).width = 300
    s.col(8).width = 300
    s.col(9).width = 300

    _transactions = StockTransaction.objects.filter(
        period=Period.objects.current()).values('product', 'type').annotate(Sum('change'))

    transactions = {}
    for t in _transactions:
        transactions.setdefault(t['product'], {})[t['type']] = t['change__sum']

    for product in plata.product_model().objects.all().select_related():
        s.write(row, 0, unicode(product))
        s.write(row, 1, product.sku)
        s.write(row, 2, product.items_in_stock)

        col = 10
        for type_id, type_name in StockTransaction.TYPE_CHOICES:
            if product.id in transactions:
                s.write(row, col, transactions[product.id].get(type_id, ''))
            col += 1

        row += 1

    return workbook
