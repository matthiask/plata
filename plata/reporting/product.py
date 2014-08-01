from __future__ import absolute_import, unicode_literals

from collections import defaultdict

from django.db.models import Sum
from django.utils.text import capfirst
from django.utils.translation import ugettext as _

import plata
from plata.reporting.utils import XLSDocument


def product_xls():
    """
    Create a list of all product variations, including stock and aggregated
    stock transactions (by type)
    """

    from plata.product.stock.models import Period
    StockTransaction = plata.stock_model()

    xls = XLSDocument()
    xls.add_sheet(capfirst(_('products')))

    _transactions = StockTransaction.objects.filter(
        period=Period.objects.current(),
        ).order_by().values('product', 'type').annotate(Sum('change'))

    transactions = defaultdict(dict)
    for t in _transactions:
        transactions[t['product']][t['type']] = t['change__sum']

    titles = [
        capfirst(_('product')),
        _('SKU'),
        capfirst(_('stock')),
    ]
    titles.extend(
        '%s' % row[1] for row in StockTransaction.TYPE_CHOICES)

    data = []

    for product in plata.product_model().objects.all().select_related():
        row = [
            product,
            getattr(product, 'sku', ''),
            getattr(product, 'items_in_stock', -1),
            ]
        row.extend(
            transactions[product.id].get(key, '')
            for key, name in StockTransaction.TYPE_CHOICES)
        data.append(row)

    xls.table(titles, data)
    return xls
