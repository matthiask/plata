from decimal import Decimal

from django.test import TestCase

#from pasta.contact.models import Contact
from pasta import pasta_settings
from pasta.product.models import TaxClass, Product
from pasta.shop.models import Contact, Order


class OrderTest(TestCase):
    def setUp(self):
        pasta_settings.PASTA_PRICE_INCLUDES_TAX = True

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

        self.assertEqual(product.get_price(order.currency).currency, order.currency)

        order.modify(product, 3)
        item = order.modify(product, -1)

        self.assertEqual(item.quantity, 2)

        item_price = Decimal('79.90')
        line_item_price = item_price * item.quantity
        order_total = Decimal('159.80')
        tax_factor = Decimal('1.076')

        self.assertAlmostEqual(order.items_subtotal, order_total / tax_factor)
        self.assertAlmostEqual(order.items_subtotal + order.items_tax, order_total)
        self.assertAlmostEqual(order.total, order_total)

        self.assertAlmostEqual(item._unit_price, item_price / tax_factor)
        self.assertAlmostEqual(item.total, line_item_price)


        self.assertAlmostEqual(item.unit_price, item_price)
        self.assertAlmostEqual(item.line_item_price, line_item_price)
        self.assertAlmostEqual(item.line_item_discount, 0)
        self.assertAlmostEqual(item.discounted_line_item_price, line_item_price)
        self.assertAlmostEqual(item.total, line_item_price)

        # Switch around tax handling and re-test
        pasta_settings.PASTA_PRICE_INCLUDES_TAX = False

        self.assertAlmostEqual(item.unit_price, item_price / tax_factor)
        self.assertAlmostEqual(item.line_item_price, line_item_price / tax_factor)
        self.assertAlmostEqual(item.line_item_discount, 0 / tax_factor)
        self.assertAlmostEqual(item.discounted_line_item_price, line_item_price / tax_factor)
        self.assertAlmostEqual(item.total, line_item_price) # NOT divided with tax_factor!

        # Switch tax handling back
        pasta_settings.PASTA_PRICE_INCLUDES_TAX = True

        print item.__dict__
        print order.__dict__
