from django.core.exceptions import ImproperlyConfigured
from django.db import models

import plata
import plata.shop.models as shop_models
from plata.product.stock import models as stock_models


if plata.settings.PLATA_STOCK_TRACKING:
    product_model = plata.product_model()
    try:
        product_model._meta.get_field("items_in_stock")
    except models.FieldDoesNotExist:
        raise ImproperlyConfigured(
            f"Product model {product_model!r} must have a field named `items_in_stock`"
        )

    models.signals.post_delete.connect(
        stock_models.update_items_in_stock, sender=stock_models.StockTransaction
    )
    models.signals.post_save.connect(
        stock_models.update_items_in_stock, sender=stock_models.StockTransaction
    )

    shop_models.Order.register_validator(
        stock_models.validate_order_stock_available, shop_models.Order.VALIDATE_CART
    )
