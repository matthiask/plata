from django.apps import AppConfig
from django.db import models
from django.core.exceptions import ImproperlyConfigured

import plata
from plata.product.stock.models import update_items_in_stock



class PlataProductStockConfig(AppConfig):
    name = 'plata.product.stock'
    verbose_name = 'Plata stock product  module'

    def ready(self):
        if plata.settings.PLATA_STOCK_TRACKING:
            product_model = plata.product_model()
            try:
                product_model._meta.get_field('items_in_stock')
            except models.FieldDoesNotExist:
                raise ImproperlyConfigured(
                    'Product model %r must have a field named `items_in_stock`' % (
                    product_model,N
            ))
