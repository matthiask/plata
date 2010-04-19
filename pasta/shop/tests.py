from decimal import Decimal

from django.test import TestCase

#from pasta.contact.models import Contact
from pasta.product.models import TaxClass, Product
from pasta.shop.models import Contact, Order


class OrderTest(TestCase):
    def create_contact(self):
        return Contact.objects.create(
            billing_first_name=u'Hans',
            billing_last_name=u'Muster',
            shipping_same_as_billing=True,
            )

    def create_order(self, contact=None):
        contact = contact or self.create_contact()

        return Order.objects.create(
            contact=contact,
            currency='CHF',
            )

    def create_product(self):
        tax_class = TaxClass.objects.create(
            name='Standard Swiss Tax Rate',
            rate=Decimal('7.60'),
            )

        product = Product.objects.create(
            name='Test Product 1',
            )

        product.prices.create(
            currency='CHF',
            tax_class=tax_class,
            _unit_price=Decimal('79.90'),
            tax_included=True,
            )

        return product

    def test_01_basic_order(self):
        product = self.create_product()
        order = self.create_order()

        order.modify(product, 3)
        item = order.modify(product, -1)

        self.assertEqual(item.quantity, 2)

        self.assertAlmostEqual(order.items_subtotal,
            Decimal('159.80') / Decimal('1.076'))
        self.assertAlmostEqual(order.items_subtotal + order.items_tax,
            Decimal('159.80'))

        print order.__dict__
