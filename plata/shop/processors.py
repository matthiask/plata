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
        tax = cost_incl_tax * tax_rate / 100
        return cost_incl_tax - tax, tax

    def set_processor_value(self, group, key, value):
        self.processor.state.setdefault(group, {})[key] = value

    def get_processor_value(self, group, key=None):
        dic = self.processor.state.get(group, {})
        if key:
            return dic.get(key)
        return dic

    def process(self, instance, items):
        raise NotImplementedError


class InitializeOrderProcessor(ProcessorBase):
    def process(self, instance, items):
        instance.items_subtotal = instance.items_tax = instance.items_discount = 0

        for item in items:
            # Recalculate item stuff
            item._line_item_price = item.quantity * item._unit_price
            item._line_item_discount = 0


class DiscountProcessor(ProcessorBase):
    def process(self, instance, items):
        for applied in instance.applied_discounts.all():
            applied.apply(instance, items)


class TaxProcessor(ProcessorBase):
    def process(self, instance, items):
        for item in items:
            taxable = item._line_item_price - (item._line_item_discount or 0)
            item._line_item_tax = taxable * item.tax_class.rate/100
            item.save()


class ItemSummationProcessor(ProcessorBase):
    def process(self, instance, items):
        for item in items:
            instance.items_subtotal += item._line_item_price
            instance.items_discount += item._line_item_discount or 0
            instance.items_tax += item._line_item_tax

        self.set_processor_value('total', 'items',
            instance.items_subtotal - instance.items_discount + instance.items_tax)


class ShippingProcessor(ProcessorBase):
    def process(self, instance, items):
        instance.shipping_tax = 0

        subtotal = 0

        if instance.shipping_cost:
            subtotal += instance.shipping_cost
        if instance.shipping_discount:
            subtotal -= instance.shipping_discount

        subtotal = max(subtotal, 0)

        # TODO move this into shipping processor
        instance.shipping_tax = subtotal * Decimal('0.076')

        self.set_processor_value('total', 'shipping',
            subtotal + instance.shipping_tax)


class OrderSummationProcessor(ProcessorBase):
    def process(self, instance, items):
        """
        The value must be quantized here, because otherwise f.e. the payment
        modules will be susceptible to rounding errors giving f.e. missing
        payments of 0.01 units.
        """

        instance.total = sum(
            self.get_processor_value('total').values(),
            Decimal('0.00'),
            ).quantize(Decimal('0.00'))
