from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _


class ProcessorBase(object):
    name = 'unnamed'

    def __init__(self, shop):
        self.shop = shop

    @property
    def urls(self):
        return self.get_urls()

    def get_urls(self):
        raise NotImplementedError

    def process_order_confirmed(self, request, order):
        raise NotImplementedError
