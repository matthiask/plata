import os
import re

from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.exceptions import ValidationError

import plata
from plata.contact.models import Contact
from plata.discount.models import Discount
from plata.product.stock.models import Period, StockTransaction
from plata.shop.models import Order, OrderPayment

from plata.tests.base import PlataTest, get_request


Product = plata.product_model()


class ViewTest(PlataTest):
    def setUp(self):
        self.ORIG_TEMPLATE_DIRS = settings.TEMPLATE_DIRS
        settings.TEMPLATE_DIRS = (os.path.join(os.path.dirname(__file__), 'templates'),)

    def tearDown(self):
        settings.TEMPLATE_DIRS = self.ORIG_TEMPLATE_DIRS

    def test_01_cart_empty(self):
        """Test cart is empty redirects work properly"""
        self.assertContains(self.client.get('/cart/'), 'Cart is empty')
        self.assertRedirects(self.client.get('/checkout/'), '/cart/')
        self.assertRedirects(self.client.get('/discounts/'), '/cart/')
        self.assertRedirects(self.client.get('/confirmation/'), '/cart/')

    def test_02_authenticated_user_has_contact(self):
        """Test shop.contact_from_user works correctly"""
        user = User.objects.create_user('test', 'test@example.com', 'testing')
        self.client.login(username='test', password='testing')

        contact = Contact.objects.create(user=user)
        shop = plata.shop_instance()

        request = get_request(user=user)

        self.assertEqual(shop.contact_from_user(request.user), contact)

    def test_03_product_detail(self):
        """Test product detail view and cart handling methods"""
        # Removed everything -- the minimal add to cart form is really,
        # really stupid. Nothing to test here.

    def test_04_shopping(self):
        """Test shopping, checkout and order PDF generation in one go"""
        self.assertEqual(Order.objects.count(), 0)
        p1 = self.create_product()
        p2 = self.create_product()
        p2.name = 'Test Product 2'
        p2.save()

        p1.stock_transactions.create(type=StockTransaction.PURCHASE, change=100)
        p2.stock_transactions.create(type=StockTransaction.PURCHASE, change=100)
        self.assertEqual(Product.objects.filter(items_in_stock=0).count(), 0)

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

        self.assertEqual(Order.objects.get().status, Order.CART)
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

        self.client.get('/checkout/')
        self.assertEqual(Order.objects.get().status, Order.CHECKOUT)

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
            'order-notes': 'Test\n\nJust testing.',
            }), '/discounts/')

        self.assertContains(self.client.post('/discounts/', {
            'code': 'something-invalid',
            }), 'not validate')

        Discount.objects.create(
            is_active=True,
            type=Discount.PERCENTAGE_VOUCHER,
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

        self.assertRedirects(self.client.post(p2.get_absolute_url(), {
            'quantity': 42,
            }), '/cart/', target_status_code=302)
        self.assertRedirects(self.client.post('/cart/', {
            'items-INITIAL_FORMS': 1,
            'items-TOTAL_FORMS': 1,
            'items-MAX_NUM_FORMS': 1,

            'items-0-id': i2.id,
            'items-0-quantity': 43,
            'items-0-DELETE': False,
            }), '/confirmation/?confirmed=1')
        self.assertTrue(Order.objects.all()[0].items.get(product=p2).quantity != 42)

        # Test this view works at all
        self.client.get('/order/payment_failure/')

        self.assertEqual(len(mail.outbox), 0)
        self.assertRedirects(self.client.post('/confirmation/', {
            'terms_and_conditions': True,
            'payment_method': 'plata.payment.modules.cod',
            }), '/order/success/')
        self.assertEqual(len(mail.outbox), 2) # invoice and packing slip
        self.assertEqual(Order.objects.get(pk=order.id).status, Order.COMPLETED)

        # Clear order
        self.assertRedirects(self.client.get('/order/new/?next=%s' % p1.get_absolute_url()),
            p1.get_absolute_url())
        # Can call URL several times without change in behavior
        self.assertRedirects(self.client.get('/order/new/'), '/',
            target_status_code=302)

        # Cart is empty
        self.assertRedirects(self.client.post('/confirmation/', {
            'terms_and_conditions': True,
            'payment_method': 'plata.payment.modules.cod',
            }), '/cart/')

        self.assertRedirects(self.client.post('/confirmation/', {
            'terms_and_conditions': True,
            'payment_method': 'plata.payment.modules.paypal',
            }), '/cart/')

        user = User.objects.create_superuser('admin', 'admin@example.com', 'password')

        self.client.login(username='admin', password='password')
        self.assertEqual(self.client.get('/reporting/invoice_pdf/%s/' % order.id)['Content-Type'],
            'application/pdf')
        self.assertEqual(self.client.get('/reporting/packing_slip_pdf/%s/' % order.id)['Content-Type'],
            'application/pdf')
        self.assertEqual(self.client.get('/reporting/product_xls/')['Content-Type'],
            'application/vnd.ms-excel')

    def test_05_creation(self):
        """Test creation of orders through the shop object"""
        shop = plata.shop_instance()
        request = get_request()

        order = shop.order_from_request(request)
        self.assertEqual(order, None)

        order = shop.order_from_request(request, create=True)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(order.user, None)

    def test_06_postfinance_ipn(self):
        """Test Postfinance server-to-server request handling"""
        shop = plata.shop_instance()
        request = get_request()

        product = self.create_product()

        Period.objects.create(name='Test period')
        product.stock_transactions.create(type=StockTransaction.PURCHASE, change=10)
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

        self.assertContains(self.client.get('/order/success/'),
            '<h1>Order has been partially paid.</h1>')

        # Revert manipulation
        order.paid += 10
        order.save()
        self.assertRedirects(self.client.get('/checkout/'), '/order/success/')

    def test_07_paypal_ipn(self):
        """Test PayPal Instant Payment Notification handler"""
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
        product.stock_transactions.create(type=StockTransaction.PURCHASE, change=10)
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
        """Test checkout behavior using already existing user without contact"""
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

        self.assertEqual(len(mail.outbox), 0)
        checkout_data['order-email'] = 'something@example.com'
        self.assertRedirects(self.client.post('/checkout/', checkout_data),
            '/discounts/')
        self.assertEqual(len(mail.outbox), 1)

        # There should be exactly one contact object now
        contact = Contact.objects.get()
        self.assertEqual(contact.user.orders.count(), 1)
        self.assertEqual(contact.billing_city, 'Beispielstadt')

        # User e-mail address is unchanged
        self.assertEqual(contact.user.email, 'test@example.com')

    def test_09_checkout_create_user(self):
        """Test checkout behavior without existing user or contact"""
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

        self.assertEqual(len(mail.outbox), 0)
        checkout_data['order-email'] = 'something@example.com'
        self.assertRedirects(self.client.post('/checkout/', checkout_data),
            '/discounts/')
        self.assertEqual(len(mail.outbox), 1)

        # There should be exactly one contact object now
        contact = Contact.objects.get()
        self.assertEqual(contact.user.orders.count(), 1)
        self.assertEqual(contact.billing_city, 'Beispielstadt')

        self.assertEqual(contact.user.email, 'something@example.com')

        # New order
        self.client.post(p1.get_absolute_url(), {'quantity': 5})
        response = self.client.get('/checkout/')

        self.assertContains(response, 'value="something@example.com"')
        self.assertContains(response, 'value="Beispielstadt"')

    def test_10_login_in_checkout_preexisting_contact(self):
        """Test checkout behavior using already existing contact and user"""
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

        self.assertEqual(len(mail.outbox), 0)
        self.assertRedirects(self.client.post('/checkout/', checkout_data),
            '/discounts/')
        self.assertEqual(len(mail.outbox), 0)

        contact = Contact.objects.get()
        # First name should be updated in checkout processing
        self.assertEqual(contact.billing_first_name, 'Fritz')
        self.assertEqual(unicode(contact), 'else@example.com') # Username

        # Order should be assigned to contact
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(contact.user.orders.count(), 1)

    def test_11_login_in_checkout_create_contact(self):
        """Test checkout using already existing user, but no contact"""
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
        self.assertEqual(contact.user.orders.count(), 1)

    def test_12_insufficient_stock(self):
        """Test insufficient stock handling in checkout process"""
        p1 = self.create_product(stock=10)
        self.client.post(p1.get_absolute_url(), {'quantity': 9})

        p1.stock_transactions.create(type=StockTransaction.SALE, change=-5)

        response = self.client.get('/checkout/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://testserver/cart/')

        self.assertContains(self.client.get('/cart/'),
            'Not enough stock available for')

    def test_13_expired_reservation(self):
        """Test payment process reservation expiration"""
        p1 = self.create_product(stock=10)

        p1.stock_transactions.create(
            type=StockTransaction.PAYMENT_PROCESS_RESERVATION,
            change=-7)

        self.assertEqual(StockTransaction.objects.items_in_stock(p1), 3)
        StockTransaction.objects.update(created=datetime.now()-timedelta(minutes=10))
        self.assertEqual(StockTransaction.objects.items_in_stock(p1), 3)
        StockTransaction.objects.update(created=datetime.now()-timedelta(minutes=20))
        self.assertEqual(StockTransaction.objects.items_in_stock(p1), 10)

        order = self.create_order()
        order.modify_item(p1, relative=5)
        order.validate(order.VALIDATE_ALL)

        StockTransaction.objects.update(created=datetime.now()-timedelta(minutes=10))
        self.assertRaises(ValidationError, order.validate, order.VALIDATE_ALL)

    def test_14_remaining_discount(self):
        """Test that a new discount is created when there is an amount remaining"""
        p1 = self.create_product(stock=10)
        self.client.post(p1.get_absolute_url(), {'quantity': 5})

        discount = Discount.objects.create(
            name='Testname',
            type=Discount.AMOUNT_VOUCHER_INCL_TAX,
            value=1000,
            config='{"all":{}}',
            tax_class=self.tax_class,
            currency='CHF',
            )

        self.assertRedirects(self.client.post('/discounts/', {
            'code': discount.code,
            'proceed': 'True',
            }), '/confirmation/')

        self.assertRedirects(self.client.post('/confirmation/', {
            'terms_and_conditions': True,
            'payment_method': 'plata.payment.modules.cod',
            }), '/order/success/')

        self.assertEqual(Discount.objects.count(), 2)

        order = Order.objects.get()
        new_discount = Discount.objects.exclude(code=discount.code).get()

        self.assertAlmostEqual(
            discount.value - sum(item.subtotal for item in order.items.all()),
            new_discount.value * (1 + self.tax_class.rate / 100))

        self.client.get('/order/new/')

        self.client.post(p1.get_absolute_url(), {'quantity': 1})
        self.assertRedirects(self.client.post('/discounts/', {
            'code': new_discount.code,
            'proceed': 'True',
            }), '/confirmation/')

        self.assertRedirects(self.client.post('/confirmation/', {
            'terms_and_conditions': True,
            'payment_method': 'plata.payment.modules.cod',
            }), '/order/success/')

        self.client.get('/order/new/')
        self.client.get('/order/new/') # Should not do anything the second time
        self.client.post(p1.get_absolute_url(), {'quantity': 1})
        self.assertContains(self.client.post('/discounts/', {
            'code': new_discount.code,
            'proceed': 'True',
            }), 'Allowed uses for this discount has already been reached.')

        # Stock transactions must be created for orders which are paid from the start
        # 10 purchase, -5 sale, -1 sale
        self.assertEqual(StockTransaction.objects.count(), 3)
        p1 = Product.objects.get(pk=p1.pk)
        self.assertEqual(p1.items_in_stock, 4)
