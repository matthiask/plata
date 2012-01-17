from decimal import Decimal, ROUND_HALF_UP

import plata
from plata.discount.models import DiscountBase


class ProcessorBase(object):
    """
    Order processor class base. Offers helper methods for order total
    aggregation and tax calculation.
    """

    def __init__(self, shared_state):
        self.shared_state = shared_state

    def split_cost(self, cost_incl_tax, tax_rate):
        """Split a cost incl. tax into the part excl. tax and the tax"""

        cost_incl_tax, tax_rate = Decimal(cost_incl_tax), Decimal(tax_rate)

        cost_excl_tax = cost_incl_tax / (1 + tax_rate / 100)
        return cost_excl_tax, cost_incl_tax - cost_excl_tax

    def add_tax_details(self, tax_details, tax_rate, price, discount, tax_amount):
        """
        Add tax details grouped by tax_rate. Especially useful if orders
        potentially use more than one tax class.
        """

        zero = Decimal('0.00')
        discount = discount or zero

        row = tax_details.setdefault(tax_rate, {
            'prices': zero,
            'discounts': zero,
            'tax_rate': tax_rate,
            'tax_amount': zero,
            'total': zero,
            })
        row['prices'] += price
        row['discounts'] += discount
        row['tax_amount'] += tax_amount

        row['total'] += price - discount + tax_amount

    def set_processor_value(self, group, key, value):
        self.shared_state.setdefault(group, {})[key] = value

    def get_processor_value(self, group, key=None):
        dic = self.shared_state.get(group, {})
        if key:
            return dic.get(key)
        return dic

    def process(self, order, items):
        """This is the method which must be implemented in order processor classes."""
        raise NotImplementedError


class InitializeOrderProcessor(ProcessorBase):
    """
    Zero out all relevant order values and calculate line item prices
    excl. tax.
    """

    def process(self, order, items):
        order.items_subtotal = order.items_tax = order.items_discount = Decimal('0.00')

        for item in items:
            # Recalculate item stuff
            item._line_item_price = item.quantity * item._unit_price
            item._line_item_discount = Decimal('0.00')


class DiscountProcessor(ProcessorBase):
    """
    Apply all discounts which do not act as a means of payment but instead
    act on the subtotal
    """

    def process(self, order, items):
        remaining = Decimal('0.00')

        for applied in order.applied_discounts.exclude(type=DiscountBase.MEANS_OF_PAYMENT):
            applied.apply(order, items)
            remaining += applied.remaining

        discounts = order.data.get('discounts', {})
        discounts['remaining_subtotal'] = remaining
        order.data['discounts'] = discounts


class MeansOfPaymentDiscountProcessor(ProcessorBase):
    """
    Apply all discounts which act as a means of payment.
    """

    def process(self, order, items):
        remaining = Decimal('0.00')

        for applied in order.applied_discounts.filter(type=DiscountBase.MEANS_OF_PAYMENT):
            applied.apply(order, items)
            remaining += applied.remaining

        discounts = order.data.get('discounts', {})
        discounts['remaining_means_of_payment'] = remaining
        order.data['discounts'] = discounts


class TaxProcessor(ProcessorBase):
    """
    Calculate taxes for every line item and aggregate tax details.
    """

    def process(self, order, items):
        tax_details = {}

        for item in items:
            taxable = item._line_item_price - (item._line_item_discount or 0)
            item._line_item_tax = (taxable * item.tax_rate/100).quantize(Decimal('0.0000000000'))

            self.add_tax_details(tax_details, item.tax_rate, item._line_item_price,
                item._line_item_discount, item._line_item_tax)

        order.data['tax_details'] = tax_details.items()


class ItemSummationProcessor(ProcessorBase):
    """
    Sum up line item prices, discounts and taxes.
    """

    def process(self, order, items):
        for item in items:
            order.items_subtotal += item._line_item_price
            order.items_discount += item._line_item_discount or 0
            order.items_tax += item._line_item_tax

        self.set_processor_value('total', 'items',
            order.items_subtotal - order.items_discount + order.items_tax)


class ZeroShippingProcessor(ProcessorBase):
    """
    Set shipping costs to zero.
    """

    def process(self, order, items):
        order.shipping_cost = order.shipping_discount = order.shipping_tax = 0

        # Not strictly necessary
        self.set_processor_value('total', 'shipping', 0)


class FixedAmountShippingProcessor(ProcessorBase):
    """
    Set shipping costs to a fixed value. Uses ``PLATA_SHIPPING_FIXEDAMOUNT``.
    If you have differing needs you should probably implement your own
    shipping processor (and propose it for inclusion if you like) instead
    of extending this one.

    ::

        PLATA_SHIPPING_FIXEDAMOUNT = {'cost': Decimal('8.00'), 'tax': Decimal('19.6')}
    """

    def process(self, order, items):
        cost = plata.settings.PLATA_SHIPPING_FIXEDAMOUNT['cost']
        tax = plata.settings.PLATA_SHIPPING_FIXEDAMOUNT['tax']

        order.shipping_cost, __ = self.split_cost(cost, tax)
        order.shipping_discount = min(order.discount_remaining, order.shipping_cost)
        order.shipping_tax = tax / 100 * (order.shipping_cost - order.shipping_discount)

        self.set_processor_value('total', 'shipping',
            order.shipping_cost - order.shipping_discount + order.shipping_tax)

        tax_details = dict(order.data.get('tax_details', []))
        self.add_tax_details(tax_details, tax, order.shipping_cost,
            order.shipping_discount, order.shipping_tax)
        order.data['tax_details'] = tax_details.items()


class ApplyRemainingDiscountToShippingProcessor(ProcessorBase):
    """
    Apply the remaining discount to the shipping (if shipping is non-zero
    and there are any remaining discounts left)
    """

    def process(self, order, items):
        raise NotImplementedError(
            "ApplyRemainingDiscountToShippingProcessor is not implemented yet")


class OrderSummationProcessor(ProcessorBase):
    """
    Sum up order total by adding up items and shipping totals.
    """

    def process(self, order, items):
        """
        The value must be quantized here, because otherwise f.e. the payment
        modules will be susceptible to rounding errors giving f.e. missing
        payments of 0.01 units.
        """

        total = sum(
            self.get_processor_value('total').values(),
            Decimal('0.00'),
            )

        order.total = total.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
