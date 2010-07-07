from decimal import Decimal

from django.core.urlresolvers import get_callable

import plata


class OrderProcessor(object):
    def __init__(self):
        self.state = {}
        self.processor_classes = [get_callable(processor)\
            for processor in plata.settings.PLATA_ORDER_PROCESSORS]

    def load_processors(self):
        return [cls(self) for cls in self.processor_classes]

    def process(self, order, items):
        for p in self.load_processors():
            p.process(order, items)


class ProcessorBase(object):
    def __init__(self, processor):
        self.processor = processor

    def split_cost(self, cost_incl_tax, tax_rate):
        cost_incl_tax, tax_rate = Decimal(cost_incl_tax), Decimal(tax_rate)

        cost_excl_tax = cost_incl_tax / (1 + tax_rate / 100)
        return cost_excl_tax, cost_incl_tax - cost_excl_tax

    def set_processor_value(self, group, key, value):
        self.processor.state.setdefault(group, {})[key] = value

    def get_processor_value(self, group, key=None):
        dic = self.processor.state.get(group, {})
        if key:
            return dic.get(key)
        return dic

    def process(self, order, items):
        raise NotImplementedError


class InitializeOrderProcessor(ProcessorBase):
    def process(self, order, items):
        order.items_subtotal = order.items_tax = order.items_discount = Decimal('0.00')

        for item in items:
            # Recalculate item stuff
            item._line_item_price = item.quantity * item._unit_price
            item._line_item_discount = Decimal('0.00')


class DiscountProcessor(ProcessorBase):
    def process(self, order, items):
        for applied in order.applied_discounts.all():
            applied.apply(order, items)


class TaxProcessor(ProcessorBase):
    def process(self, order, items):
        for item in items:
            taxable = item._line_item_price - (item._line_item_discount or 0)
            item._line_item_tax = taxable * item.tax_class.rate/100
            item.save()


class ItemSummationProcessor(ProcessorBase):
    def process(self, order, items):
        for item in items:
            order.items_subtotal += item._line_item_price
            order.items_discount += item._line_item_discount or 0
            order.items_tax += item._line_item_tax

        self.set_processor_value('total', 'items',
            order.items_subtotal - order.items_discount + order.items_tax)


class ZeroShippingProcessor(ProcessorBase):
    def process(self, order, items):
        order.shipping_cost = order.shipping_discount = order.shipping_tax = 0

        # Not strictly necessary
        self.set_processor_value('total', 'shipping', 0)


class FixedAmountShippingProcessor(ProcessorBase):
    def process(self, order, items):
        cost = plata.settings.PLATA_SHIPPING_FIXEDAMOUNT['cost']
        tax = plata.settings.PLATA_SHIPPING_FIXEDAMOUNT['tax']

        order.shipping_cost, __ = self.split_cost(cost, tax)
        order.shipping_discount = min(order.discount_remaining, order.shipping_cost)
        order.shipping_tax = tax / 100 * (order.shipping_cost - order.shipping_discount)

        self.set_processor_value('total', 'shipping',
            order.shipping_cost - order.shipping_discount + order.shipping_tax)


class OrderSummationProcessor(ProcessorBase):
    def process(self, order, items):
        """
        The value must be quantized here, because otherwise f.e. the payment
        modules will be susceptible to rounding errors giving f.e. missing
        payments of 0.01 units.
        """

        order.total = sum(
            self.get_processor_value('total').values(),
            Decimal('0.00'),
            ).quantize(Decimal('0.00'))
