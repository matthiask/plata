import os

from datetime import date, datetime
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

import plata
from plata.contact.models import Contact, ContactUser
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

        contact = Contact.objects.create(email=user.email)
        ContactUser.objects.create(contact=contact, user=user)
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

        Period.objects.create(name='Test period')

        self.assertContains(self.client.post('/confirmation/', {
            'payment_method': 'plata.payment.modules.postfinance',
            }), 'SHASign')

        self.assertContains(self.client.post('/confirmation/', {
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
            'payment_method': 'plata.payment.modules.cod',
            }), '/order/success/')
        self.assertEqual(Order.objects.get(pk=order.id).status, Order.COMPLETED)

        self.assertRedirects(self.client.post('/confirmation/', {
            'payment_method': 'plata.payment.modules.cod',
            }), '/cart/?empty=1')

        self.assertRedirects(self.client.post('/confirmation/', {
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

        shop.set_contact_on_request(request, contact=None)
        self.assertEqual(shop.contact_from_request(request, create=False), None)

    def test_06_postfinance_ipn(self):
        shop = plata.shop_instance()
        request = get_request()

        product = self.create_product()
        self.client.post(product.get_absolute_url(), {
            'quantity': 5,
            })

        Period.objects.create(name='Test period')

        response = self.client.post('/confirmation/', {
            'payment_method': 'plata.payment.modules.postfinance',
            })
        self.assertContains(response, 'SHASign')
        self.assertContains(response, '721735bc3876094bb7e5ff075de8411d85494a66')

        self.assertEqual(StockTransaction.objects.count(), 1)
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

        self.assertEqual(StockTransaction.objects.count(), 3)

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
        self.client.post(product.get_absolute_url(), {
            'quantity': 5,
            })

        Period.objects.create(name='Test period')

        response = self.client.post('/confirmation/', {
            'payment_method': 'plata.payment.modules.paypal',
            })
        self.assertContains(response, 'sandbox')

        self.assertEqual(StockTransaction.objects.count(), 1)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderPayment.objects.count(), 1)

        self.assertContains(self.client.post('/payment/paypal/ipn/',
            paypal_ipn_data), 'Ok')

        order = Order.objects.get(pk=1)
        assert order.is_paid()

        self.assertEqual(StockTransaction.objects.count(), 3)
