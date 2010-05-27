from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _

from plata.product.stock.models import StockTransaction


class ProcessorBase(object):
    name = 'unnamed'

    def __init__(self, shop):
        self.shop = shop

    @property
    def urls(self):
        return self.get_urls()

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        return patterns('')

    def process_order_confirmed(self, request, order):
        raise NotImplementedError

    def create_transactions(self, order, stage, **kwargs):
        StockTransaction.objects.bulk_create(order,
            notes=_('%(stage)s: %(order)s processed by %(payment_module)s') % {
                'stage': stage,
                'order': order,
                'payment_module': self.name,
                },
            **kwargs)
