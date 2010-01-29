from datetime import datetime
from decimal import Decimal

from django.db import models
from django.utils.translation import ugettext_lazy as _

from pasta.product.models import Product


class OrderProcessor(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def apply(self, order, items, state, **kwargs):
        pass

        # Processing has completed
        return True


class PriceProcessor(OrderProcessor):
    def apply(self, order, items, state, **kwargs):
        for item in items:
            item.price = item.quantity * item.product.unit_price
        return True


class TaxProcessor(OrderProcessor):
    pass

class ShippingProcessor(OrderProcessor):
    pass

class AutomaticDiscount(OrderProcessor):
    def apply(self, order, items, state, **kwargs):
        for item in items:
            if not hasattr(item, 'discount'):
                item.discount = Decimal('1.00')
                item.price -= item.discount
        return True

class PercentageDiscount(OrderProcessor):
    pass

class AmountDiscount(OrderProcessor):
    pass




class Order(models.Model):
    processor_classes = {}

    created = models.DateTimeField(_('created'), default=datetime.now)

    @classmethod
    def register_processor(cls, sequence_nr, processor):
        cls.processor_classes['%02d_%s' % (sequence_nr, processor.__name__)] =\
            processor

    @classmethod
    def remove_processor(cls, processor):
        for k, v in cls.processor_classes.iteritems():
            if v == processor:
                del cls.processor_classes[k]

    def recalculate_items(self, items, **kwargs):
        state = {
            'pass': 0,
            }

        processors = dict((k, v()) for k, v in self.processor_classes.iteritems())
        keys = sorted(processors.keys())

        while keys:
            state['pass'] += 1

            toremove = [key for key in keys if \
                processors[key].apply(self, items, state, **kwargs) != False]
            keys = [key for key in keys if key not in toremove]

            if state['pass'] > 10:
                raise Exception('Too many passes while recalculating order total.')

        print state


Order.register_processor(10, PriceProcessor)
Order.register_processor(20, PercentageDiscount)
Order.register_processor(21, AutomaticDiscount)
Order.register_processor(30, TaxProcessor)
Order.register_processor(40, ShippingProcessor)
Order.register_processor(50, AmountDiscount)



class OrderItem(models.Model):
    order = models.ForeignKey(Order)
    product = models.ForeignKey(Product)

    quantity = models.IntegerField(_('amount'))

    """
    unit_price = models.DecimalField(_('unit price'), max_digits=18, decimal_places=10)
    unit_tax = models.DecimalField(_('unit tax'), max_digits=18, decimal_places=10)

    line_item_price = models.DecimalField(_('line item price'), max_digits=18, decimal_places=10)
    line_item_tax = models.DecimalField(_('line item tax'), max_digits=18, decimal_places=10)

    discount = models.DecimalField(_('discount'), max_digits=18, decimal_places=10)
    """





class PriceProcessor(object):
    def product_price(self, product):
        pass

    def line_item_price(self, line_item):
        pass

