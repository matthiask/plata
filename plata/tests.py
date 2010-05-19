import os
import random

from datetime import date, datetime
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import ValidationError
from django.test import TestCase

import plata
from plata import plata_settings
from plata.contact.models import Contact
from plata.product.models import TaxClass, Product, ProductVariation, Discount
from plata.product.stock.models import Period, StockTransaction
from plata.shop.models import Order, OrderStatus, OrderPayment


class Empty(object):
    pass


def get_request(**kwargs):
    """
    Helper method which creates a mock request object
    """

    request = Empty()
    request.session = {}
    request.user = AnonymousUser()

    for k, v in kwargs.items():
       setattr(request, k, v)

    return request


class PlataTest(TestCase):
    def assertRaisesWithCode(self, exception, fn, code):
        try:
            fn()
        except exception, e:
            if e.code == code:
                return True
            raise
        raise Exception, '%s did not raise %s' % (fn, exception)

    def setUp(self):
        plata_settings.PLATA_PRICE_INCLUDES_TAX = True

    def create_contact(self):
        return Contact.objects.create(
            billing_company=u'BigCorp',
            billing_first_name=u'Hans',
            billing_last_name=u'Muster',
            billing_address=u'Musterstrasse 42',
            billing_zip_code=u'8042',
            billing_city=u'Beispielstadt',
            billing_country=u'CH',
            shipping_same_as_billing=True,
            currency='CHF',
            )

    def create_order(self, contact=None):
        contact = contact or self.create_contact()

        return Order.objects.create(
            contact=contact,
            currency='CHF',
            )

    def create_tax_classes(self):
        self.tax_class, created = TaxClass.objects.get_or_create(
            name='Standard Swiss Tax Rate',
            rate=Decimal('7.60'),
            )

        self.tax_class_germany, created = TaxClass.objects.get_or_create(
            name='Umsatzsteuer (Germany)',
            rate=Decimal('19.60'),
            )

        self.tax_class_something, created = TaxClass.objects.get_or_create(
            name='Some tax rate',
            rate=Decimal('12.50'),
            )

        return self.tax_class, self.tax_class_germany, self.tax_class_something


    def create_product(self):
        tax_class, tax_class_germany, tax_class_something = self.create_tax_classes()

        product = Product.objects.create(
            name='Test Product 1',
            slug='prod%s' % random.random(),
            )

        product.variations.create()

        # An old price in CHF which should not influence the rest of the tests
        product.prices.create(
            currency='CHF',
            tax_class=tax_class,
            _unit_price=Decimal('99.90'),
            tax_included=True,
            )

        product.prices.create(
            currency='CHF',
            tax_class=tax_class,
            _unit_price=Decimal('79.90'),
            tax_included=True,
            )

        product.prices.create(
            currency='EUR',
            tax_class=tax_class_germany,
            _unit_price=Decimal('49.90'),
            tax_included=True,
            )

        product.prices.create(
            currency='ASDF',
            tax_class=tax_class_something,
            _unit_price=Decimal('65.00'),
            tax_included=False,
            )

        # A few prices which are not yet (or no more) active
        product.prices.create(
            currency='CHF',
            tax_class=tax_class,
            _unit_price=Decimal('110.00'),
            tax_included=True,
            is_active=False,
            )

        product.prices.create(
            currency='CHF',
            tax_class=tax_class,
            _unit_price=Decimal('120.00'),
            tax_included=True,
            is_active=True,
            valid_from=date(2100, 1, 1),
            )

        product.prices.create(
            currency='CHF',
            tax_class=tax_class,
            _unit_price=Decimal('130.00'),
            tax_included=True,
            is_active=True,
            valid_from=date(2000, 1, 1),
            valid_until=date(2001, 1, 1),
            )

        return product


class OrderTest(PlataTest):
    def test_01_basic_order(self):
        product = self.create_product()
        order = self.create_order()

        self.assertEqual(product.get_price(currency=order.currency).currency, order.currency)

        order.modify_item(product, 5)
        order.modify_item(product, -4)
        item = order.modify_item(product, 1)

        self.assertEqual(order.items.count(), 1)

        self.assertEqual(item.quantity, 2)

        item_price = Decimal('79.90')
        line_item_price = item_price * item.quantity
        order_total = Decimal('159.80')
        tax_factor = Decimal('1.076')

        self.assertAlmostEqual(order.items_subtotal, order_total / tax_factor)
        self.assertAlmostEqual(order.items_subtotal + order.items_tax, order_total)
        self.assertAlmostEqual(order.total, order_total)

        self.assertAlmostEqual(item._unit_price, item_price / tax_factor)
        self.assertAlmostEqual(item.discounted_subtotal_incl_tax, line_item_price)
        self.assertAlmostEqual(item.discounted_subtotal_excl_tax, line_item_price / tax_factor)
        self.assertAlmostEqual(item.discounted_subtotal_incl_tax, line_item_price)

        self.assertAlmostEqual(item.unit_price, item_price)
        self.assertAlmostEqual(item.line_item_discount, 0)
        self.assertAlmostEqual(item.discounted_subtotal, item.discounted_subtotal_incl_tax)

        # Switch around tax handling and re-test
        plata_settings.PLATA_PRICE_INCLUDES_TAX = False

        self.assertAlmostEqual(item.unit_price, item_price / tax_factor)
        self.assertAlmostEqual(item.line_item_discount, 0 / tax_factor)
        self.assertAlmostEqual(item.discounted_subtotal, item.discounted_subtotal_excl_tax)

        # Switch tax handling back
        plata_settings.PLATA_PRICE_INCLUDES_TAX = True

    def test_02_eur_order(self):
        product = self.create_product()
        order = self.create_order()

        order.currency = 'EUR'
        order.save()

        item = order.modify_item(product, 2)

        self.assertEqual(item.unit_price, Decimal('49.90'))
        self.assertEqual(item.currency, order.currency)

    def test_03_mixed_currencies(self):
        """
        Create an invalid order
        """

        p1 = self.create_product()
        p2 = self.create_product()
        order = self.create_order()

        order.currency = 'CHF'
        i1 = order.modify_item(p1, 3)

        order.currency = 'EUR'
        self.assertRaisesWithCode(ValidationError, lambda: order.modify_item(p2, 2),
            code='multiple_currency')

        # Validation should still fail
        self.assertRaisesWithCode(ValidationError, lambda: order.validate(),
            code='multiple_currency')

        order.currency = 'CHF'
        # Order should validate now
        order.validate()

    def test_04_order_modify_item(self):
        p1 = self.create_product()
        p2 = self.create_product()
        order = self.create_order()

        order.modify_item(p1, 42)
        order.modify_item(p2, 42)
        self.assertEqual(order.items.count(), 2)

        order.modify_item(p1, -42)
        self.assertEqual(order.items.count(), 1)

        item = order.modify_item(p1, relative=3)
        self.assertEqual(item.quantity, 3)
        item = order.modify_item(p1, relative=2)
        self.assertEqual(item.quantity, 5)
        item = order.modify_item(p1, absolute=33)
        self.assertEqual(item.quantity, 33)

    def test_05_order_status(self):
        order = self.create_order()

        self.assertRaisesWithCode(ValidationError, lambda: order.update_status(
            Order.CHECKOUT,
            'Checkout process has started',
            ), code='order_empty')

        product = self.create_product()
        order.modify_item(product, 1)

        # Should be possible to update order status now
        order.update_status(
            Order.CONFIRMED,
            'Order has been confirmed',
            )

        # Should not be possible to modify order once checkout process has started
        self.assertRaisesWithCode(ValidationError, lambda: order.modify_item(product, 2),
            code='order_sealed')

        self.assertEqual(order.status, Order.CONFIRMED)

    def test_06_order_percentage_discount(self):
        order = self.create_order()
        p1 = self.create_product()
        p2 = self.create_product()

        order.modify_item(p1, 3)
        order.modify_item(p2, 5)

        discount = Discount.objects.create(
            is_active=False,
            type=Discount.PERCENTAGE,
            code='asdf',
            name='Percentage discount',
            value=30)

        self.assertRaises(ValidationError, lambda: order.add_discount(discount))
        discount.is_active = True
        discount.save()

        order.add_discount(discount)
        order.recalculate_total()

        tax_factor = Decimal('1.076')
        item_price_incl_tax = Decimal('79.90')
        item_price_excl_tax = item_price_incl_tax / tax_factor

        order.recalculate_total()
        item = order.modify_item(p1, relative=0)
        item2 = order.modify_item(p2, relative=0)

        self.assertAlmostEqual(item.unit_price, item_price_incl_tax)
        self.assertAlmostEqual(item.line_item_discount, item_price_incl_tax * 3 * Decimal('0.30'))
        self.assertAlmostEqual(order.total,
            item.discounted_subtotal + item2.discounted_subtotal)

        plata_settings.PLATA_PRICE_INCLUDES_TAX = False
        order.recalculate_total()
        item = order.modify_item(p1, 0)
        item2 = order.modify_item(p2, 0)

        self.assertAlmostEqual(item.unit_price, item_price_excl_tax)
        self.assertAlmostEqual(item.line_item_discount, item_price_excl_tax * 3 * Decimal('0.30'))
        self.assertAlmostEqual(order.total,
            item.discounted_subtotal + item2.discounted_subtotal + order.items_tax)

        plata_settings.PLATA_PRICE_INCLUDES_TAX = True

    def test_07_order_amount_discount(self):
        order = self.create_order()
        p1 = self.create_product()
        p2 = self.create_product()

        normal1 = order.modify_item(p1, 3)
        normal2 = order.modify_item(p2, 5)

        order.recalculate_total()
        self.assertAlmostEqual(order.total, Decimal('639.20'))

        discount = Discount.objects.create(
            type=Discount.AMOUNT_INCL_TAX,
            code='asdf',
            name='Amount discount',
            value=Decimal('50.00'),
            is_active=True)
        order.add_discount(discount)
        order.recalculate_total()

        discounted1 = order.modify_item(p1, 0)
        discounted2 = order.modify_item(p2, 0)

        tax_factor = Decimal('1.076')
        item_price_incl_tax = Decimal('79.90')
        item_price_excl_tax = item_price_incl_tax / tax_factor

        self.assertAlmostEqual(order.total, Decimal('639.20') - Decimal('50.00'))

        self.assertAlmostEqual(normal1.unit_price, discounted1.unit_price)
        self.assertAlmostEqual(normal2.unit_price, discounted2.unit_price)
        self.assertAlmostEqual(normal1.unit_price, item_price_incl_tax)

        self.assertEqual(normal1.line_item_discount, 0)
        self.assertEqual(normal2.line_item_discount, 0)

        self.assertAlmostEqual(discounted1.line_item_discount, Decimal('50.00') / 8 * 3)
        self.assertAlmostEqual(discounted2.line_item_discount, Decimal('50.00') / 8 * 5)

        self.assertAlmostEqual(discounted1.discounted_subtotal, order.total / 8 * 3)
        self.assertAlmostEqual(discounted2.discounted_subtotal, order.total / 8 * 5)

        plata_settings.PLATA_PRICE_INCLUDES_TAX = False
        order.recalculate_total()
        discounted1 = order.modify_item(p1, 0)
        discounted2 = order.modify_item(p2, 0)

        self.assertAlmostEqual(order.total, Decimal('639.20') - Decimal('50.00'))

        self.assertAlmostEqual(discounted1.unit_price, item_price_excl_tax)
        self.assertAlmostEqual(discounted1.line_item_discount, discount.value / tax_factor / 8 * 3)
        self.assertAlmostEqual(order.total,
            discounted1.discounted_subtotal + discounted2.discounted_subtotal + order.items_tax)

        plata_settings.PLATA_PRICE_INCLUDES_TAX = True

    def test_08_order_payment(self):
        order = self.create_order()
        product = self.create_product()

        order.modify_item(product, 10)
        order.recalculate_total()

        payment = order.payments.model(
            order=order,
            currency='CHF',
            amount=Decimal('49.90'),
            payment_method='Mafia style',
            )

        # The descriptor cannot be used through create(), therefore
        # we need this stupid little dance
        payment.data_json = {'anything': 42}
        payment.save()

        order = Order.objects.get(pk=order.pk)
        self.assertAlmostEqual(order.paid, 0)

        payment.authorized = datetime.now()
        payment.save()

        order = Order.objects.get(pk=order.pk)
        self.assertAlmostEqual(order.balance_remaining, order.total - payment.amount)

        self.assertEqual(order.payments.all()[0].data_json['anything'], 42)

    def test_09_selective_discount(self):
        p1 = self.create_product()
        p2 = self.create_product()
        p2.name = 'Discountable'
        p2.save()

        d = Discount(
            type=Discount.PERCENTAGE,
            name='Some discount',
            code='asdf',
            value=Decimal('30'),
            is_active=True,
            )

        d.data_json = {
            'eligible_filter': {
                'name__icontains': 'countable',
                },
            }

        d.save()

        self.assertEqual(Product.objects.all().count(), 2)
        self.assertEqual(d.eligible_products(Product.objects.all()).count(), 1)
        self.assertEqual(d.eligible_products().count(), 1)

        order = self.create_order()
        order.modify_item(p1, 3)
        order.modify_item(p2, 2)
        order.add_discount(d)
        order.recalculate_total()

        # Test that only one order item has its discount applied
        self.assertEqual(1,
            len([item for item in order.items.all() if item._line_item_discount]))


    def test_10_discount_validation(self):
        order = self.create_order()
        d = Discount(
            is_active=False,
            valid_from=date(2100, 1, 1), # far future date
            valid_until=None,
            )

        try:
            d.validate(order)
        except ValidationError, e:
            self.assertEqual(len(e.messages), 2)

        d.is_active = True
        d.valid_until = date(2000, 1, 1)

        try:
            d.validate(order)
        except ValidationError, e:
            self.assertEqual(len(e.messages), 2)

    def test_11_multiple_discounts(self):
        order = self.create_order()
        product = self.create_product()
        order.modify_item(product, 3)
        order.recalculate_total()

        self.assertAlmostEqual(order.total, Decimal('239.70'))

        order.add_discount(Discount.objects.create(
            type=Discount.PERCENTAGE,
            name='Percentage',
            code='perc20',
            value=Decimal('20.00'),
            is_active=True,
            ))
        order.recalculate_total()

        self.assertAlmostEqual(order.total, Decimal('239.70') / 5 * 4)

        order.add_discount(Discount.objects.create(
            type=Discount.AMOUNT_INCL_TAX,
            name='Amount incl. tax',
            code='amount_incl_20',
            value=Decimal('20.00'),
            is_active=True,
            ))
        order.recalculate_total()

        self.assertAlmostEqual(order.total, Decimal('239.70') / 5 * 4 - 20)

    def test_12_order4567_test(self):
        order = self.create_order()

        p1 = self.create_product()
        p1.name = 'Kleid'
        p1.save()
        p1.prices.all().delete()
        p1.prices.create(
            _unit_price=160,
            tax_included=True,
            currency=order.currency,
            tax_class=self.tax_class,
            )

        p2 = self.create_product()
        p2.prices.all().delete()
        p2.prices.create(
            _unit_price=280,
            tax_included=True,
            currency=order.currency,
            tax_class=self.tax_class,
            )

        order.modify_item(p1, 1)
        order.modify_item(p2, 1)

        self.assertAlmostEqual(order.total, Decimal('440.00'))

        discount = Discount(
            type=Discount.PERCENTAGE,
            name='Sonderrabatt Kleid',
            value=Decimal('20.00'),
            code='1234code',
            )
        discount.data_json = {
            'eligible_filter': {
                'name__icontains': 'Kleid',
                },
            }
        discount.save()

        order.add_discount(discount)
        order.recalculate_total()

        self.assertAlmostEqual(order.total, 408)
        self.assertAlmostEqual(order.subtotal, 440)
        self.assertAlmostEqual(order.discount, 32)
        # TODO add 8.00 shipping

    def test_13_order4206_test(self):
        order = self.create_order()

        p1 = self.create_product()
        p1.name = 'Venice'
        p1.save()
        p1.prices.all().delete()
        p1.prices.create(
            _unit_price=170,
            tax_included=True,
            currency=order.currency,
            tax_class=self.tax_class,
            )

        p2 = self.create_product()
        p2.prices.all().delete()
        p2.prices.create(
            _unit_price=Decimal('40.80'),
            tax_included=True,
            currency=order.currency,
            tax_class=self.tax_class,
            )

        order.modify_item(p1, 1)
        order.modify_item(p2, 1)

        discount = Discount(
            type=Discount.AMOUNT_INCL_TAX,
            name='Sonderrabatt Venice',
            value=Decimal('20.00'),
            code='1234code',
            )
        discount.data_json = {
            'eligible_filter': {
                'name__icontains': 'Venice',
                },
            }
        discount.save()

        order.add_discount(discount)
        order.recalculate_total()

        self.assertAlmostEqual(order.total, Decimal('190.80'))
        self.assertAlmostEqual(order.subtotal, Decimal('210.80'))
        self.assertAlmostEqual(order.discount, 20)
        # TODO add 8.00 shipping

    def test_14_invoice2009_0170_0002_test(self):
        order = self.create_order()

        p = self.create_product()
        p.prices.all().delete()
        p.prices.create(
            _unit_price=1,
            tax_included=False,
            currency=order.currency,
            tax_class=self.tax_class,
            )

        order.modify_item(p, 952)
        order.modify_item(p, 120)

        discount = Discount.objects.create(
            type=Discount.AMOUNT_EXCL_TAX,
            name='Discount',
            value=532,
            code='1234code',
            )
        order.add_discount(discount)

        order.recalculate_total()

        plata_settings.PLATA_PRICE_INCLUDES_TAX = False
        self.assertAlmostEqual(order.subtotal, Decimal('1072.00'))
        self.assertAlmostEqual(order.discount, Decimal('532.00'))
        self.assertAlmostEqual(order.items_tax, Decimal('41.04'))
        self.assertAlmostEqual(order.total, Decimal('581.04'))
        plata_settings.PLATA_PRICE_INCLUDES_TAX = True

    def test_15_remaining_discount(self):
        order = self.create_order()
        product = self.create_product()

        order.modify_item(product, 1)
        self.assertAlmostEqual(order.total, Decimal('79.90'))

        order.add_discount(Discount.objects.create(
            type=Discount.AMOUNT_INCL_TAX,
            name='Discount',
            value='100',
            code='1234code',
            ))

        self.assertAlmostEqual(order.subtotal, Decimal('79.90'))
        self.assertAlmostEqual(order.discount, Decimal('79.90'))
        self.assertAlmostEqual(order.total, 0)
        self.assertAlmostEqual(order.discount_remaining, Decimal('20.10'))

    def test_16_payment(self):
        order = self.create_order()
        product = self.create_product()

        order.modify_item(product, 3)
        self.assertAlmostEqual(order.balance_remaining, Decimal('79.90') * 3)

        payment = order.payments.create(
            currency=order.currency,
            amount=100,
            )

        self.assertAlmostEqual(order.balance_remaining, Decimal('79.90') * 3)

        payment.transaction_id = '1234' # Not strictly required
        payment.authorized = datetime.now()
        payment.save()

        order = Order.objects.get(pk=order.pk)
        self.assertAlmostEqual(order.balance_remaining, Decimal('139.70'))

        order.payments.create(
            currency=order.currency,
            amount=Decimal('139.70'),
            authorized=datetime.now(),
            )

        order = Order.objects.get(pk=order.pk)
        self.assertAlmostEqual(order.balance_remaining, Decimal('0.00'))
        self.assertTrue(order.is_paid)

        payment.delete()
        order = Order.objects.get(pk=order.pk)
        self.assertAlmostEqual(order.balance_remaining, Decimal('100.00'))

    def test_17_stocktransactions(self):
        order = self.create_order()
        product = self.create_product()
        variation = product.variations.get()

        period = Period.objects.create(
            name='Period 1',
            start=datetime.now(),
            )
        # Create a period which has been superceeded by Period 1
        Period.objects.create(
            name='Period 0',
            start=datetime(2000, 1, 1, 0, 0),
            )

        # Create a period in the far future
        Period.objects.create(
            name='Period 2',
            start=datetime(2100, 1, 1, 0, 0),
            )

        s = StockTransaction.objects.create(
            product=variation,
            type=StockTransaction.INITIAL,
            change=10,
            )

        self.assertEqual(s.period, period)
        self.assertEqual(ProductVariation.objects.get(pk=variation.id).items_in_stock, 10)

        StockTransaction.objects.create(
            product=variation,
            type=StockTransaction.CORRECTION,
            change=-3,
            )

        self.assertEqual(StockTransaction.objects.items_in_stock(variation), 7)

        StockTransaction.objects.create(
            product=variation,
            type=StockTransaction.SALE,
            change=-2,
            )

        StockTransaction.objects.create(
            product=variation,
            type=StockTransaction.PURCHASE,
            change=4,
            )

        StockTransaction.objects.open_new_period(name='Something')

        transaction = StockTransaction.objects.filter(product=variation)[0]

        self.assertEqual(transaction.type, StockTransaction.INITIAL)
        self.assertEqual(transaction.change, 9)
        self.assertEqual(transaction.period.name, 'Something')


class ShopTest(PlataTest):
    def test_01_creation(self):
        shop = plata.shop_instance()
        request = get_request()

        contact = shop.contact_from_request(request)
        self.assertEqual(contact, None)

        contact = shop.contact_from_request(request, create=True)
        self.assertNotEqual(contact, None)

        contact = shop.contact_from_request(request, create=True)
        self.assertEqual(Contact.objects.count(), 1)

        order = shop.order_from_request(request)
        self.assertEqual(order, None)

        order = shop.order_from_request(request, create=True)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(order.contact, contact)


class ViewTest(PlataTest):
    def setUp(self):
        self.ORIG_TEMPLATE_DIRS = settings.TEMPLATE_DIRS
        settings.TEMPLATE_DIRS = (os.path.join(os.path.dirname(__file__), 'templates'),)

    def tearDown(self):
        settings.TEMPLATE_DIRS = self.ORIG_TEMPLATE_DIRS

    def test_01_cart_empty(self):
        self.assertContains(self.client.get('/cart/'), 'Cart is empty')
        self.assertRedirects(self.client.get('/checkout/'), '/cart/?empty=1')
        self.assertRedirects(self.client.get('/confirmation/'), '/cart/?empty=1')

    def test_02_authenticated_user_has_contact(self):
        user = User.objects.create_user('test', 'test@example.com', 'testing')
        self.client.login(username='test', password='testing')

        contact = Contact.objects.create(email=user.email, user=user)
        shop = plata.shop_instance()

        request = get_request(user=user)

        self.assertEqual(shop.contact_from_request(request), contact)

    def test_03_authenticated_user_has_no_contact(self):
        user = User.objects.create_user('test', 'test@example.com', 'testing')
        self.client.login(username='test', password='testing')
        shop = plata.shop_instance()

        self.assertEqual(Contact.objects.count(), 0)
        contact = shop.contact_from_request(get_request(user=user), create=True)

        self.assertEqual(user.email, contact.email)
        self.assertEqual(Contact.objects.count(), 1)

    def test_04_shopping(self):
        self.assertEqual(Order.objects.count(), 0)
        p1 = self.create_product()
        p2 = self.create_product()

        self.assertContains(self.client.get(p1.get_absolute_url()),
            p1.name)

        self.client.post(p1.get_absolute_url(), {
            'quantity': 5,
            })
        self.client.post(p2.get_absolute_url(), {
            'quantity': 3,
            })

        self.assertEqual(Order.objects.count(), 1)
        self.assertContains(self.client.get('/cart/'), 'value="5"')

        order = Order.objects.all()[0]
        i1 = order.modify_item(p1, 0)
        i2 = order.modify_item(p2, 0)

        self.assertRedirects(self.client.post('/cart/', {
            'items-INITIAL_FORMS': 2,
            'items-TOTAL_FORMS': 2,
            'items-MAX_NUM_FORMS': 2,

            'items-0-id': i1.id,
            'items-0-quantity': 6, # one additional item

            'items-1-id': i2.id,
            'items-1-quantity': i2.quantity,
            }), '/cart/')

        self.assertEqual(order.modify_item(p1, 0).quantity, 6)

        self.assertRedirects(self.client.post('/cart/', {
            'checkout': True,

            'items-INITIAL_FORMS': 2,
            'items-TOTAL_FORMS': 2,
            'items-MAX_NUM_FORMS': 2,

            'items-0-id': i1.id,
            'items-0-quantity': 6, # one additional item

            'items-1-id': i2.id,
            'items-1-quantity': 0,
            }), '/checkout/')

        self.assertEqual(order.modify_item(p1, 0).quantity, 6)
        self.assertEqual(order.items.count(), 1)

        self.client.post(p2.get_absolute_url(), {
            'quantity': 5,
            })
        self.assertEqual(order.items.count(), 2)

        self.assertRedirects(self.client.post('/cart/', {
            'checkout': True,

            'items-INITIAL_FORMS': 2,
            'items-TOTAL_FORMS': 2,
            'items-MAX_NUM_FORMS': 2,

            'items-0-id': i1.id,
            'items-0-quantity': 6,
            'items-0-DELETE': True,

            'items-1-id': i2.id,
            'items-1-quantity': 5,
            }), '/checkout/')
        self.assertEqual(order.items.count(), 1)

        self.assertEqual(self.client.post('/checkout/', {
            'contact-billing_company': u'BigCorp',
            'contact-billing_first_name': u'Hans',
            'contact-billing_last_name': u'Muster',
            'contact-billing_address': u'Musterstrasse 42',
            'contact-billing_zip_code': u'8042',
            'contact-billing_city': u'Beispielstadt',
            'contact-billing_country': u'CH',
            #'contact-shipping_same_as_billing': True, # billing information is missing...
            'contact-email': 'something@example.com',
            'contact-currency': 'CHF',
            }).status_code, 200) # ... therefore view does not redirect

        self.assertRedirects(self.client.post('/checkout/', {
            'contact-billing_company': u'BigCorp',
            'contact-billing_first_name': u'Hans',
            'contact-billing_last_name': u'Muster',
            'contact-billing_address': u'Musterstrasse 42',
            'contact-billing_zip_code': u'8042',
            'contact-billing_city': u'Beispielstadt',
            'contact-billing_country': u'CH',
            'contact-shipping_same_as_billing': True,
            'contact-email': 'something@example.com',
            'contact-currency': 'CHF',
            }), '/confirmation/')

        self.client.post('/confirmation/', {})
        self.assertEqual(Order.objects.get(pk=order.id).status, Order.CONFIRMED)

        self.assertEqual(self.client.get('/pdf/%s/' % order.id)['Content-Type'],
            'application/pdf')
