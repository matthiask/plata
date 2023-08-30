from django import apps
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.db.models import signals

import plata


class AppConfig(apps.AppConfig):
    name = "plata.product.stock"

    def ready(self):
        if plata.settings.PLATA_STOCK_TRACKING:
            product_model = plata.product_model()
            try:
                product_model._meta.get_field("items_in_stock")
            except FieldDoesNotExist:
                raise ImproperlyConfigured(
                    f"Product model {product_model!r} must have a field named"
                    " `items_in_stock`"
                )

            from plata.product.stock.models import (
                StockTransaction,
                update_items_in_stock,
                validate_order_stock_available,
            )
            from plata.shop.models import Order

            signals.post_delete.connect(update_items_in_stock, sender=StockTransaction)
            signals.post_save.connect(update_items_in_stock, sender=StockTransaction)

            Order.register_validator(
                validate_order_stock_available, Order.VALIDATE_CART
            )
