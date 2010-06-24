import os
import re

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

import plata
from plata.contact.models import Contact
from plata.discount.models import Discount
from plata.product.models import TaxClass, Product, ProductVariation,\
    ProductPrice, OptionGroup, Option
from plata.product.stock.models import Period, StockTransaction
from plata.shop.models import Order, OrderStatus, OrderPayment

from plata.tests.base import PlataTest, get_request


class ViewTest(PlataTest):
    def setUp(self):
        self.ORIG_TEMPLATE_DIRS = settings.TEMPLATE_DIRS
        settings.TEMPLATE_DIRS = (os.path.join(os.path.dirname(__file__), 'templates'),)

    def tearDown(self):
        settings.TEMPLATE_DIRS = self.ORIG_TEMPLATE_DIRS

    def test_01_cart_empty(self):
        self.assertContains(self.client.get('/cart/'), 'Cart is empty')
        self.assertRedirects(self.client.get('/checkout/'), '/cart/?empty=1')
        self.assertRedirects(self.client.get('/discounts/'), '/cart/?empty=1')
        self.assertRedirects(self.client.get('/confirmation/'), '/cart/?empty=1')

    def test_02_authenticated_user_has_contact(self):
        user = User.objects.create_user('test', 'test@example.com', 'testing')
        self.client.login(username='test', password='testing')

        contact = Contact.objects.create(user=user)
        shop = plata.shop_instance()

        request = get_request(user=user)

        self.assertEqual(shop.contact_from_user(request.user), contact)

    def test_03_product_detail(self):
        p1 = self.create_product()
        response = self.client.post(p1.get_absolute_url(), {
            'quantity': 5,
            })
        self.assertTrue(re.search(r'Only \d+ items for .*available', response.content))

        p1.variations.get().stock_transactions.create(type=StockTransaction.PURCHASE, change=100)
        self.assertRedirects(self.client.post(p1.get_absolute_url(), {'quantity': 5}),
            p1.get_absolute_url())

        p1.variations.all().delete()
        self.assertContains(self.client.post(p1.get_absolute_url(), {'quantity': 5}),
            'The requested product does not exist.')

        group = OptionGroup.objects.create(name='color')
        group.options.create(name='red', value='red')
        group.options.create(name='green', value='green')
        group.options.create(name='blue', value='blue')
        p1.option_groups.add(group)

        group = OptionGroup.objects.create(name='size')
        group.options.create(name='s', value='s')
        group.options.create(name='m', value='m')

        option = group.options.create(name='l', value='l')

        self.assertEqual(unicode(option), 'l')
        self.assertEqual(option.full_name(), 'size - l')
        p1.option_groups.add(group)

        p1.create_variations()
        self.assertEqual(p1.variations.count(), 9)

        self.assertContains(self.client.post(p1.get_absolute_url(), {'quantity': 5}),
            'This field is required', count=2)
        self.assertContains(self.client.post(p1.get_absolute_url(), {
            'quantity': 5,
            'option_1': 1,
            }), 'This field is required', count=1)

        response = self.client.post(p1.get_absolute_url(), {
            'quantity': 5,
            'option_1': 1,
            'option_2': 5,
            })
        self.assertTrue(re.search(r'Only \d+ items for .*available', response.content))

        variation = p1.variations.filter(options__id=1).filter(options__id=5).get()
        variation.stock_transactions.create(type=StockTransaction.PURCHASE, change=100)

        self.assertRedirects(self.client.post(p1.get_absolute_url(), {
            'quantity': 5,
            'option_1': 1,
            'option_2': 5,
            }), p1.get_absolute_url())

        p1.create_variations()
        p1.prices.all().delete()
        self.assertContains(self.client.post(p1.get_absolute_url(), {
            'quantity': 5,
            'option_1': 1,
            'option_2': 5,
            }), 'Price could not be determined', count=1)

    def test_04_shopping(self):
        self.assertEqual(Order.objects.count(), 0)
        p1 = self.create_product()
        p2 = self.create_product()
        p2.name = 'Test Product 2'
        p2.save()

        p1.variations.get().stock_transactions.create(type=StockTransaction.PURCHASE, change=100)
        p2.variations.get().stock_transactions.create(type=StockTransaction.PURCHASE, change=100)
        self.assertEqual(ProductVariation.objects.filter(items_in_stock=0).count(), 0)

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
            '_checkout': 1,
            'order-billing_company': u'BigCorp',
            'order-billing_first_name': u'Hans',
            'order-billing_last_name': u'Muster',
            'order-billing_address': u'Musterstrasse 42',
            'order-billing_zip_code': u'8042',
            'order-billing_city': u'Beispielstadt',
            'order-billing_country': u'CH',
            #'order-shipping_same_as_billing': True, # billing information is missing...
            'order-email': 'something@example.com',
            'order-currency': 'CHF',
            }).status_code, 200) # ... therefore view does not redirect

        self.assertRedirects(self.client.post('/checkout/', {
            '_checkout': 1,
            'order-billing_company': u'BigCorp',
            'order-billing_first_name': u'Hans',
            'order-billing_last_name': u'Muster',
            'order-billing_address': u'Musterstrasse 42',
            'order-billing_zip_code': u'8042',
            'order-billing_city': u'Beispielstadt',
            'order-billing_country': u'CH',
            'order-shipping_same_as_billing': True,
            'order-email': 'something@example.com',
            'order-currency': 'CHF',
            }), '/discounts/')

        self.assertContains(self.client.post('/discounts/', {
            'code': 'something-invalid',
            }), 'not validate')

        Discount.objects.create(
            is_active=True,
            type=Discount.PERCENTAGE,
            code='asdf',
            name='Percentage discount',
            value=30)

        self.assertRedirects(self.client.post('/discounts/', {
            'code': 'asdf',
            }), '/discounts/')

        self.assertRedirects(self.client.post('/discounts/', {
            'proceed': 'True',
            }), '/confirmation/')

        self.assertEqual(self.client.post('/confirmation/', {}).status_code, 200)
        self.assertEqual(Order.objects.get(pk=order.id).status, Order.CHECKOUT)

        self.assertContains(self.client.post('/confirmation/', {
            'terms_and_conditions': True,
            'payment_method': 'plata.payment.modules.postfinance',
            }), 'SHASign')

        self.assertContains(self.client.post('/confirmation/', {
            'terms_and_conditions': True,
            'payment_method': 'plata.payment.modules.paypal',
            }), 'cgi-bin/webscr')

        # Should not modify order anymore
        self.assertRedirects(self.client.post(p2.get_absolute_url(), {
            'quantity': 42,
            }), p2.get_absolute_url())
        self.assertRedirects(self.client.post('/cart/', {
            'items-INITIAL_FORMS': 1,
            'items-TOTAL_FORMS': 1,
            'items-MAX_NUM_FORMS': 1,

            'items-0-id': i2.id,
            'items-0-quantity': 43,
            'items-0-DELETE': False,
            }), '/confirmation/?confirmed=1')
        self.assertTrue(Order.objects.all()[0].items.get(variation__product=p2).quantity != 42)

        self.assertRedirects(self.client.post('/confirmation/', {
            'terms_and_conditions': True,
            'payment_method': 'plata.payment.modules.cod',
            }), '/order/success/')
        self.assertEqual(Order.objects.get(pk=order.id).status, Order.COMPLETED)

        self.assertRedirects(self.client.post('/confirmation/', {
            'terms_and_conditions': True,
            'payment_method': 'plata.payment.modules.cod',
            }), '/cart/?empty=1')

        self.assertRedirects(self.client.post('/confirmation/', {
            'terms_and_conditions': True,
            'payment_method': 'plata.payment.modules.paypal',
            }), '/cart/?empty=1')


        user = User.objects.create_superuser('admin', 'admin@example.com', 'password')

        self.client.login(username='admin', password='password')
        self.assertEqual(self.client.get('/reporting/order_pdf/%s/' % order.id)['Content-Type'],
            'application/pdf')
        self.assertEqual(self.client.get('/reporting/product_xls/')['Content-Type'],
            'application/vnd.ms-excel')

    def test_05_creation(self):
        shop = plata.shop_instance()
        request = get_request()

        order = shop.order_from_request(request)
        self.assertEqual(order, None)

        order = shop.order_from_request(request, create=True)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(order.contact, None)

    def test_06_postfinance_ipn(self):
        shop = plata.shop_instance()
        request = get_request()

        product = self.create_product()
        self.client.post(product.get_absolute_url(), {
            'quantity': 5,
            })

        Period.objects.create(name='Test period')
        product.variations.get().stock_transactions.create(type=StockTransaction.PURCHASE, change=10)
        self.client.post(product.get_absolute_url(), {
            'quantity': 5,
            })

        response = self.client.post('/confirmation/', {
            'terms_and_conditions': True,
            'payment_method': 'plata.payment.modules.postfinance',
            })
        self.assertContains(response, 'SHASign')
        self.assertContains(response, '721735bc3876094bb7e5ff075de8411d85494a66')

        self.assertEqual(StockTransaction.objects.count(), 2)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderPayment.objects.count(), 1)

        self.assertContains(self.client.post('/payment/postfinance/ipn/', {
            }), 'Missing data', status_code=403)

        order = Order.objects.get(pk=1)

        ipn_data = {
            'orderID': 'Order-1-1',
            'currency': order.currency,
            'amount': order.balance_remaining,
            'PM': 'Postfinance',
            'ACCEPTANCE': 'xxx',
            'STATUS': '5', # Authorized
            'CARDNO': 'xxxxxxxxxxxx1111',
            'PAYID': '123456789',
            'NCERROR': '',
            'BRAND': 'VISA',
            'SHASIGN': 'this-value-is-invalid',
            }

        self.assertContains(self.client.post('/payment/postfinance/ipn/', ipn_data),
            'Hash did not validate', status_code=403)

        ipn_data['SHASIGN'] = '4b4cf5f9a5f0b54cc119be3696f43f81139232ae'

        self.assertContains(self.client.post('/payment/postfinance/ipn/', ipn_data),
            'OK', status_code=200)

        order = Order.objects.get(pk=1)
        assert order.is_paid()

        self.assertEqual(StockTransaction.objects.count(), 2)

        # Manipulate paid amount
        order.paid -= 10
        order.save()
        self.assertRedirects(self.client.get('/cart/'), '/confirmation/?confirmed=1')

        # Revert manipulation
        order.paid += 10
        order.save()
        self.assertRedirects(self.client.get('/checkout/'), '/order/already_paid/')

    def test_07_paypal_ipn(self):
        paypal_ipn_data = {
            'txn_id': '123456789',
            'invoice': 'Order-1-1',
            'mc_currency': 'CHF',
            'mc_gross': '1234',
            'payment_status': 'Completed',
            }

        from plata.payment.modules import paypal
        import cgi
        def mock_urlopen(*args, **kwargs):
            qs = cgi.parse_qs(args[1])
            assert qs['cmd'][0] == '_notify-validate'
            for k, v in paypal_ipn_data.iteritems():
                assert qs[k][0] == v

            import StringIO
            s = StringIO.StringIO('VERIFIED')
            return s
        paypal.urllib.urlopen = mock_urlopen

        shop = plata.shop_instance()
        request = get_request()

        product = self.create_product()
        product.variations.get().stock_transactions.create(type=StockTransaction.PURCHASE, change=10)
        self.client.post(product.get_absolute_url(), {
            'quantity': 5,
            })

        response = self.client.post('/confirmation/', {
            'terms_and_conditions': True,
            'payment_method': 'plata.payment.modules.paypal',
            })
        self.assertContains(response, 'sandbox')

        self.assertEqual(StockTransaction.objects.count(), 2)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderPayment.objects.count(), 1)

        self.assertContains(self.client.post('/payment/paypal/ipn/',
            paypal_ipn_data), 'Ok')

        order = Order.objects.get(pk=1)
        assert order.is_paid()

        self.assertEqual(StockTransaction.objects.count(), 2)

    def test_08_checkout_preexisting_user(self):
        User.objects.create_user('else', 'else@example.com', 'test')

        user = User.objects.create_user('test', 'test@example.com', 'test')
        self.client.login(username='test', password='test')

        p1 = self.create_product(stock=100)
        self.client.post(p1.get_absolute_url(), {'quantity': 5})

        response = self.client.get('/checkout/')
        self.assertContains(response, 'Checkout')
        self.assertNotContains(response, 'login-username')

        checkout_data = {
            '_checkout': 1,
            'order-billing_company': u'BigCorp',
            'order-billing_first_name': u'Hans',
            'order-billing_last_name': u'Muster',
            'order-billing_address': u'Musterstrasse 42',
            'order-billing_zip_code': u'8042',
            'order-billing_city': u'Beispielstadt',
            'order-billing_country': u'CH',
            'order-shipping_same_as_billing': True,
            'order-email': 'else@example.com',
            'order-currency': 'CHF',
            'order-create_account': True,
            }

        self.assertContains(self.client.post('/checkout/', checkout_data),
            'This e-mail address belongs to a different account')

        checkout_data['order-email'] = 'something@example.com'
        self.assertRedirects(self.client.post('/checkout/', checkout_data),
            '/discounts/')

        # There should be exactly one contact object now
        contact = Contact.objects.get()
        self.assertEqual(contact.orders.count(), 1)
        self.assertEqual(contact.billing_city, 'Beispielstadt')

        # User e-mail address is unchanged
        self.assertEqual(contact.user.email, 'test@example.com')

    def test_09_checkout_create_user(self):
        User.objects.create_user('else', 'else@example.com', 'test')

        p1 = self.create_product(stock=100)
        self.client.post(p1.get_absolute_url(), {'quantity': 5})

        response = self.client.get('/checkout/')
        self.assertContains(response, 'Checkout')
        self.assertContains(response, 'login-username')

        checkout_data = {
            '_checkout': 1,
            'order-billing_company': u'BigCorp',
            'order-billing_first_name': u'Hans',
            'order-billing_last_name': u'Muster',
            'order-billing_address': u'Musterstrasse 42',
            'order-billing_zip_code': u'8042',
            'order-billing_city': u'Beispielstadt',
            'order-billing_country': u'CH',
            'order-shipping_same_as_billing': True,
            'order-email': 'else@example.com',
            'order-currency': 'CHF',
            'order-create_account': True,
            }

        self.assertContains(self.client.post('/checkout/', checkout_data),
            'This e-mail address might belong to you, but we cannot know for sure because you are not authenticated yet')

        checkout_data['order-email'] = 'something@example.com'
        self.assertRedirects(self.client.post('/checkout/', checkout_data),
            '/discounts/')

        # There should be exactly one contact object now
        contact = Contact.objects.get()
        self.assertEqual(contact.orders.count(), 1)
        self.assertEqual(contact.billing_city, 'Beispielstadt')

        self.assertEqual(contact.user.email, 'something@example.com')

        # New order
        self.client.post(p1.get_absolute_url(), {'quantity': 5})
        response = self.client.get('/checkout/')

        self.assertContains(response, 'value="something@example.com"')
        self.assertContains(response, 'value="Beispielstadt"')

    def test_10_login_in_checkout_preexisting_contact(self):
        Contact.objects.create(
            user=User.objects.create_user('else@example.com', 'else@example.com', 'test'),
            currency='CHF',
            billing_first_name='Hans',
            billing_last_name='Muster',
            )

        p1 = self.create_product(stock=100)
        self.client.post(p1.get_absolute_url(), {'quantity': 5})

        response = self.client.get('/checkout/')
        self.assertContains(response, 'Checkout')
        self.assertContains(response, 'login-username')

        self.assertRedirects(self.client.post('/checkout/', {
            '_login': 1,
            'login-username': 'else@example.com',
            'login-password': 'test',
            }), '/checkout/')

        # Test that the order is still active after logging in
        response = self.client.get('/checkout/')
        self.assertContains(response, 'value="else@example.com"')
        self.assertContains(response, 'value="Muster"')

        checkout_data = {
            '_checkout': 1,
            'order-billing_company': u'BigCorp',
            'order-billing_first_name': u'Fritz',
            'order-billing_last_name': u'Muster',
            'order-billing_address': u'Musterstrasse 42',
            'order-billing_zip_code': u'8042',
            'order-billing_city': u'Beispielstadt',
            'order-billing_country': u'CH',
            'order-shipping_same_as_billing': True,
            'order-email': 'else@example.com',
            'order-currency': 'CHF',
            'order-create_account': True,
            }

        self.assertRedirects(self.client.post('/checkout/', checkout_data),
            '/discounts/')

        contact = Contact.objects.get()
        # First name should not be overwritten from checkout processing
        self.assertEqual(contact.billing_first_name, 'Hans')

        # Order should be assigned to contact
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(contact.orders.count(), 1)

    def test_11_login_in_checkout_create_contact(self):
        User.objects.create_user('else@example.com', 'else@example.com', 'test')

        p1 = self.create_product(stock=100)
        self.client.post(p1.get_absolute_url(), {'quantity': 5})

        response = self.client.get('/checkout/')
        self.assertContains(response, 'Checkout')
        self.assertContains(response, 'login-username')

        self.assertRedirects(self.client.post('/checkout/', {
            '_login': 1,
            'login-username': 'else@example.com',
            'login-password': 'test',
            }), '/checkout/')

        checkout_data = {
            '_checkout': 1,
            'order-billing_company': u'BigCorp',
            'order-billing_first_name': u'Fritz',
            'order-billing_last_name': u'Muster',
            'order-billing_address': u'Musterstrasse 42',
            'order-billing_zip_code': u'8042',
            'order-billing_city': u'Beispielstadt',
            'order-billing_country': u'CH',
            'order-shipping_same_as_billing': True,
            'order-email': 'else@example.com',
            'order-currency': 'CHF',
            'order-create_account': True,
            }

        # If order wasn't active after logging in anymore, this would not work
        self.assertRedirects(self.client.post('/checkout/', checkout_data),
            '/discounts/')

        contact = Contact.objects.get()
        self.assertEqual(contact.billing_first_name, 'Fritz')

        # Order should be assigned to contact
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(contact.orders.count(), 1)

    def test_12_insufficient_stock(self):
        p1 = self.create_product(stock=10)
        self.client.post(p1.get_absolute_url(), {'quantity': 9})

        p1.variations.get().stock_transactions.create(type=StockTransaction.SALE, change=-5)

        self.assertRedirects(self.client.get('/checkout/'),
            '/cart/?insufficient_stock=1')

    def test_13_expired_reservation(self):
        p1 = self.create_product(stock=10)

        p1.variations.get().stock_transactions.create(
            type=StockTransaction.PAYMENT_PROCESS_RESERVATION,
            change=-7)

        response = self.client.post(p1.get_absolute_url(), {'quantity': 5})
        self.assertTrue(re.search(r'Only \d+ items for .* available', response.content))

        StockTransaction.objects.update(created=datetime.now()-timedelta(minutes=10))
        response = self.client.post(p1.get_absolute_url(), {'quantity': 5})
        self.assertTrue(re.search(r'Only \d+ items for .* available', response.content))

        StockTransaction.objects.update(created=datetime.now()-timedelta(minutes=20))
        self.assertRedirects(self.client.post(p1.get_absolute_url(), {'quantity': 5}),
            p1.get_absolute_url())
