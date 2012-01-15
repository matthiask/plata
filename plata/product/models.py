"""
Product model base implementation -- you do not need to use this

It may save you some typing though.
"""

from django.db import models

import plata


class ProductBase(models.Model):
    """
    Product models must have two methods to be usable with Plata:

    - ``get_price``: Return a price instance
    - ``handle_order_item``: Fill in fields on the order item from the product,
      i.e. the name and the stock keeping unit.
    """

    class Meta:
        abstract = True

    def get_price(self, currency=None, orderitem=None):
        """
        This method is part of the public, required API of products. It returns
        either a price instance or raises a ``DoesNotExist`` exception.

        If you need more complex pricing schemes, override this method with your
        own implementation.
        """
        if currency is None:
            currency = (orderitem.currency if orderitem else
                plata.shop_instance().default_currency())

        try:
            # Let's hope that ordering=[-id] from the base price definition
            # makes any sense here :-)
            return self.prices.filter(currency=currency)[0]
        except IndexError:
            raise self.prices.model.DoesNotExist

    def handle_order_item(self, orderitem):
        """
        This method has to ensure that the information on the order item is
        sufficient for posteriority. Old orders should always be complete
        even if the products have been changed or deleted in the meantime.
        """
        orderitem.name = unicode(self)
        orderitem.sku = getattr(self, 'sku', u'')
