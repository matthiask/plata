import os

from datetime import date, datetime
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import ValidationError
from django.test import TestCase

import plata
from plata import plata_settings
from plata.contact.models import Contact
from plata.product.models import TaxClass, Product, Discount
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
        tax_class, created = TaxClass.objects.get_or_create(
            name='Standard Swiss Tax Rate',
            rate=Decimal('7.60'),
            )

        tax_class_germany, created = TaxClass.objects.get_or_create(
            name='Umsatzsteuer (Germany)',
            rate=Decimal('19.00'),
            )

        tax_class_something, created = TaxClass.objects.get_or_create(
            name='Some tax rate',
            rate=Decimal('12.50'),
            )

        return tax_class, tax_class_germany, tax_class_something


    def create_product(self):
        tax_class, tax_class_germany, tax_class_something = self.create_tax_classes()

        product = Product.objects.create(
            name='Test Product 1',
            )

        # An old price in CHF which should not influence the rest of the tests
        product.prices.create(
            currency='CHF',
            tax_class=tax_class,
            _unit_price=Decimal('99.90'),
            tax_included=True
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
            Order.CHECKOUT,
            'Checkout process has started',
            )

        # Should not be possible to modify order once checkout process has started
        self.assertRaisesWithCode(ValidationError, lambda: order.modify_item(product, 2),
            code='order_sealed')

        self.assertEqual(order.status, Order.CHECKOUT)

    def test_06_order_percentage_discount(self):
        order = self.create_order()
        p1 = self.create_product()
        p2 = self.create_product()

        order.modify_item(p1, 3)
        order.modify_item(p2, 5)

        discount = Discount.objects.create(
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
        item = order.modify_item(p1, 0)
        item2 = order.modify_item(p2, 0)

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

        d = Discount()
        d.data_json = {
            'eligible_filter': {
                'name__icontains': 'countable',
                },
            }

        self.assertEqual(Product.objects.all().count(), 2)
        self.assertEqual(d.eligible_products(Product.objects.all()).count(), 1)
        self.assertEqual(d.eligible_products().count(), 1)

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
        self.assertContains(self.client.get('/plata/cart/'), 'Cart is empty')
        self.assertRedirects(self.client.get('/plata/checkout/'), '/plata/cart/?empty=1')
        self.assertRedirects(self.client.get('/plata/confirmation/'), '/plata/cart/?empty=1')

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
        product = self.create_product()

        self.client.post('/plata/api/order_modify_item/', {
            'product': product.pk,
            'quantity': 5,
            })

        self.assertEqual(Order.objects.count(), 1)
        self.assertContains(self.client.get('/plata/cart/'), 'value="5"')

        order = Order.objects.all()[0]
        item = order.items.all()[0]

        self.assertRedirects(self.client.post('/plata/cart/', {
            'checkout': True,

            'items-INITIAL_FORMS': 1,
            'items-TOTAL_FORMS': 1,
            'items-MAX_NUM_FORMS': 1,

            'items-0-id': item.id,
            'items-0-quantity': 6, # one additional item
            }), '/plata/checkout/')

        self.assertEqual(order.modify_item(product, 0).quantity, 6)

        self.assertRedirects(self.client.post('/plata/checkout/', {
            'contact-email': 'something@example.com',
            'contact-currency': 'CHF',
            }), '/plata/confirmation/')
