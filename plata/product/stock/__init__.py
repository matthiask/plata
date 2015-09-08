from django import apps
from django.core.exceptions import ImproperlyConfigured
from django.db.models import FieldDoesNotExist, signals

import plata

default_app_config = 'plata.product.stock.AppConfig'


class AppConfig(apps.AppConfig):
    name = 'plata.product.stock'

    def ready(self):
        if plata.settings.PLATA_STOCK_TRACKING:
            product_model = plata.product_model()
            try:
                product_model._meta.get_field('items_in_stock')
            except FieldDoesNotExist:
                raise ImproperlyConfigured(
                    'Product model %r must have a field named `items_in_stock`' % (
                        product_model,
                    ))

            from plata.product.stock.models import (
                StockTransaction,
                update_items_in_stock,
                validate_order_stock_available,
            )
            from plata.shop.models import Order

            signals.post_delete.connect(
                update_items_in_stock,
                sender=StockTransaction)
            signals.post_save.connect(
                update_items_in_stock,
                sender=StockTransaction)

            Order.register_validator(
                validate_order_stock_available,
                Order.VALIDATE_CART)
