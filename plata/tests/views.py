import os

from datetime import date, datetime
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from plata import plata_settings, shop_instance
from plata.contact.models import Contact, ContactUser
from plata.product.models import TaxClass, Product, ProductVariation, Discount,\
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
        self.assertRedirects(self.client.get('/confirmation/'), '/cart/?empty=1')

    def test_02_authenticated_user_has_contact(self):
        user = User.objects.create_user('test', 'test@example.com', 'testing')
        self.client.login(username='test', password='testing')

        contact = Contact.objects.create(email=user.email)
        ContactUser.objects.create(contact=contact, user=user)
        shop = shop_instance()

        request = get_request(user=user)

        self.assertEqual(shop.contact_from_request(request), contact)

    def test_03_authenticated_user_has_no_contact(self):
        user = User.objects.create_user('test', 'test@example.com', 'testing')
        self.client.login(username='test', password='testing')
        shop = shop_instance()

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

        self.assertEqual(self.client.post('/confirmation/', {}).status_code, 200)
        self.assertEqual(Order.objects.get(pk=order.id).status, Order.CHECKOUT)

        self.assertRedirects(self.client.post('/confirmation/', {
            'payment_method': 'plata.payment.modules.cod',
            }), '/order/success/')
        self.assertEqual(Order.objects.get(pk=order.id).status, Order.CONFIRMED)

        self.assertEqual(self.client.get('/pdf/%s/' % order.id)['Content-Type'],
            'application/pdf')

    def test_05_creation(self):
        shop = shop_instance()
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

