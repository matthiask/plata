from decimal import Decimal


class OrderProcessor(object):
    def __init__(self):
        self.state = {}

    def load_processors(self):
        # TODO make this list configurable
        return [
            InitializeOrderProcessor(self),
            DiscountProcessor(self),
            TaxProcessor(self),
            ShippingProcessor(self),
            SummationProcessor(self),
            ]

    def process(self, order, items):
        for p in self.load_processors():
            p(order, items)


class ProcessorBase(object):
    def __init__(self, processor):
        self.processor = processor

    def __call__(self, instance, items):
        raise NotImplementedError


class InitializeOrderProcessor(ProcessorBase):
    def __call__(self, instance, items):
        instance.items_subtotal = instance.items_tax = instance.items_discount = 0

        for item in items:
            # Recalculate item stuff
            item._line_item_price = item.quantity * item._unit_price
            item._line_item_discount = 0


class DiscountProcessor(ProcessorBase):
    def __call__(self, instance, items):
        for applied in instance.applied_discounts.all():
            applied.apply(instance, items)


class TaxProcessor(ProcessorBase):
    def __call__(self, instance, items):
        for item in items:
            taxable = item._line_item_price - (item._line_item_discount or 0)
            price = item.get_product_price()
            item._line_item_tax = taxable * price.tax_class.rate/100
            item.save()

            # Order stuff
            instance.items_subtotal += item._line_item_price
            instance.items_discount += item._line_item_discount or 0
            instance.items_tax += item._line_item_tax

        self.processor.state.setdefault('total', {})['items'] =\
            instance.items_subtotal - instance.items_discount + instance.items_tax


class ShippingProcessor(ProcessorBase):
    def __call__(self, instance, items):
        instance.shipping_tax = 0

        subtotal = 0

        if instance.shipping_cost:
            subtotal += instance.shipping_cost
        if instance.shipping_discount:
            subtotal -= instance.shipping_discount

        subtotal = max(subtotal, 0)

        # TODO move this into shipping processor
        instance.shipping_tax = subtotal * Decimal('0.076')

        self.processor.state.setdefault('total', {})['shipping'] =\
           subtotal + instance.shipping_tax


class SummationProcessor(ProcessorBase):
    def __call__(self, instance, items):
        instance.total = sum(self.processor.state['total'].values(), 0)
