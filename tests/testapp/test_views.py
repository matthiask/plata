from __future__ import absolute_import, unicode_literals

import warnings
from datetime import timedelta
from io import BytesIO
from urllib.parse import parse_qs

import django
from django.core import mail
from django.core.exceptions import ValidationError
from django.utils import timezone

import plata
from plata.contact.models import Contact
from plata.discount.models import Discount
from plata.product.stock.models import Period, StockTransaction
from plata.shop.models import Order, OrderPayment

from .base import PlataTest, get_request


try:  # pragma: no cover
    from django.contrib.auth import get_user_model

    User = get_user_model()
except ImportError:
    from django.contrib.auth.models import User


Product = plata.product_model()


class ViewTest(PlataTest):
    def test_01_cart_empty(self):
        """Test cart is empty redirects work properly"""
        client = self.login()
        self.assertContains(client.get("/cart/"), "Cart is empty")
        self.assertRedirects(client.get("/checkout/"), "/cart/")
        self.assertRedirects(client.get("/discounts/"), "/cart/")
        self.assertRedirects(client.get("/confirmation/"), "/cart/")

    def test_02_authenticated_user_has_contact(self):
        """Test shop.contact_from_user works correctly"""
        user = User.objects.create_user("test", "test@example.com", "testing")
        self.client.login(username="test", password="testing")

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
        p2.name = "Test Product 2"
        p2.save()

        p1.stock_transactions.create(type=StockTransaction.PURCHASE, change=100)
        p2.stock_transactions.create(type=StockTransaction.PURCHASE, change=100)
        self.assertEqual(Product.objects.filter(items_in_stock=0).count(), 0)

        client = self.login()

        self.assertContains(client.get(p1.get_absolute_url()), p1.name)

        client.post(p1.get_absolute_url(), {"quantity": 5})
        client.post(p2.get_absolute_url(), {"quantity": 3})

        self.assertEqual(Order.objects.count(), 1)
        self.assertContains(client.get("/cart/"), 'value="5"')

        order = Order.objects.all()[0]
        i1 = order.modify_item(p1, 0)
        i2 = order.modify_item(p2, 0)

        self.assertRedirects(
            client.post(
                "/cart/",
                {
                    "items-INITIAL_FORMS": 2,
                    "items-TOTAL_FORMS": 2,
                    "items-MAX_NUM_FORMS": 2,
                    "items-0-id": i1.id,
                    "items-0-quantity": 6,  # one additional item
                    "items-1-id": i2.id,
                    "items-1-quantity": i2.quantity,
                },
            ),
            "/cart/",
        )

        self.assertEqual(order.modify_item(p1, 0).quantity, 6)
        self.assertEqual(order.items.count(), 2)

        self.assertRedirects(
            client.post(
                "/cart/",
                {
                    "checkout": True,
                    "items-INITIAL_FORMS": 2,
                    "items-TOTAL_FORMS": 2,
                    "items-MAX_NUM_FORMS": 2,
                    "items-0-id": i1.id,
                    "items-0-quantity": 6,  # one additional item
                    "items-1-id": i2.id,
                    "items-1-quantity": 0,
                },
            ),
            "/checkout/",
        )

        self.assertEqual(order.modify_item(p1, 0).quantity, 6)
        self.assertEqual(order.items.count(), 1)

        client.post(p2.get_absolute_url(), {"quantity": 5})
        self.assertEqual(order.items.count(), 2)

        # TODO test what happens when a product has been deleted from the
        # shop in the meantime (and orderitem.product = None)

        # Refresh i1 and i2
        i1 = order.modify_item(p1, 0)
        i2 = order.modify_item(p2, 0)

        self.assertEqual(Order.objects.get().status, Order.CART)
        response = client.post(
            "/cart/",
            {
                "checkout": True,
                "items-INITIAL_FORMS": 2,
                "items-TOTAL_FORMS": 2,
                "items-MAX_NUM_FORMS": 2,
                "items-0-id": i1.id,
                "items-0-quantity": 6,
                "items-0-DELETE": True,
                "items-1-id": i2.id,
                "items-1-quantity": 5,
            },
        )
        self.assertRedirects(response, "/checkout/")
        self.assertEqual(order.items.count(), 1)

        client.get("/checkout/")
        self.assertEqual(Order.objects.get().status, Order.CHECKOUT)

        self.assertEqual(
            client.post(
                "/checkout/",
                {
                    "_checkout": 1,
                    "order-billing_company": "BigCorp",
                    "order-billing_first_name": "Hans",
                    "order-billing_last_name": "Muster",
                    "order-billing_address": "Musterstrasse 42",
                    "order-billing_zip_code": "8042",
                    "order-billing_city": "Beispielstadt",
                    "order-billing_country": "CH",
                    # 'order-shipping_same_as_billing': True,  # information is missing
                    "order-email": "something@example.com",
                    "order-currency": "CHF",
                },
            ).status_code,
            200,
        )  # ... therefore view does not redirect

        self.assertRedirects(
            client.post(
                "/checkout/",
                {
                    "_checkout": 1,
                    "order-billing_company": "BigCorp",
                    "order-billing_first_name": "Hans",
                    "order-billing_last_name": "Muster",
                    "order-billing_address": "Musterstrasse 42",
                    "order-billing_zip_code": "8042",
                    "order-billing_city": "Beispielstadt",
                    "order-billing_country": "CH",
                    "order-shipping_same_as_billing": True,
                    "order-email": "something@example.com",
                    "order-currency": "CHF",
                    "order-notes": "Test\n\nJust testing.",
                },
            ),
            "/confirmation/",
        )

        Discount.objects.create(
            is_active=True,
            type=Discount.PERCENTAGE_VOUCHER,
            code="asdf",
            name="Percentage discount",
            value=30,
        )

        self.assertContains(
            client.post("/discounts/", {"code": "something-invalid"}), "not validate"
        )

        self.assertRedirects(
            client.post("/discounts/", {"code": "asdf"}), "/discounts/"
        )

        self.assertRedirects(
            client.post("/discounts/", {"proceed": "True"}), "/confirmation/"
        )

        self.assertEqual(client.post("/confirmation/", {}).status_code, 200)
        self.assertEqual(Order.objects.get(pk=order.id).status, Order.CHECKOUT)

        self.assertContains(
            client.post(
                "/confirmation/",
                {"terms_and_conditions": True, "payment_method": "postfinance"},
            ),
            "SHASign",
        )

        self.assertContains(
            client.post(
                "/confirmation/",
                {"terms_and_conditions": True, "payment_method": "paypal"},
            ),
            "cgi-bin/webscr",
        )

        self.assertRedirects(
            client.post(p2.get_absolute_url(), {"quantity": 42}),
            "/cart/",
            target_status_code=302,
        )
        self.assertRedirects(
            client.post(
                "/cart/",
                {
                    "items-INITIAL_FORMS": 1,
                    "items-TOTAL_FORMS": 1,
                    "items-MAX_NUM_FORMS": 1,
                    "items-0-id": i2.id,
                    "items-0-quantity": 43,
                    "items-0-DELETE": False,
                },
            ),
            "/confirmation/?confirmed=1",
        )
        self.assertTrue(Order.objects.all()[0].items.get(product=p2).quantity != 42)

        # Test this view works at all
        client.get("/order/payment_failure/")

        self.assertRedirects(
            client.post(
                "/confirmation/",
                {"terms_and_conditions": True, "payment_method": "cod"},
            ),
            "/order/success/",
        )
        self.assertEqual(
            len(mail.outbox), 3
        )  # account creation, invoice and packing slip
        self.assertEqual(Order.objects.get(pk=order.id).status, Order.PAID)

        # Clear order
        self.assertRedirects(
            client.get("/order/new/?next=%s" % p1.get_absolute_url()),
            p1.get_absolute_url(),
        )
        # Can call URL several times without change in behavior
        self.assertRedirects(client.get("/order/new/"), "/", target_status_code=302)

        # Cart is empty
        self.assertRedirects(
            client.post(
                "/confirmation/",
                {"terms_and_conditions": True, "payment_method": "cod"},
            ),
            "/cart/",
        )

        self.assertRedirects(
            client.post(
                "/confirmation/",
                {"terms_and_conditions": True, "payment_method": "paypal"},
            ),
            "/cart/",
        )

        User.objects.create_superuser("admin", "admin@example.com", "password")

        client.login(username="admin", password="password")
        self.assertEqual(
            client.get("/reporting/invoice_pdf/%s/" % order.id)["Content-Type"],
            "application/pdf",
        )
        self.assertEqual(
            client.get("/reporting/packing_slip_pdf/%s/" % order.id)["Content-Type"],
            "application/pdf",
        )
        self.assertEqual(
            client.get("/reporting/product_xls/")["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

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

        product = self.create_product()
        client = self.login()

        Period.objects.create(name="Test period")
        product.stock_transactions.create(type=StockTransaction.PURCHASE, change=10)
        client.post(product.get_absolute_url(), {"quantity": 5})

        response = client.post(
            "/confirmation/",
            {"terms_and_conditions": True, "payment_method": "postfinance"},
        )
        self.assertContains(response, "SHASign")
        self.assertContains(response, "721735bc3876094bb7e5ff075de8411d85494a66")

        self.assertEqual(StockTransaction.objects.count(), 2)
        self.assertEqual(Order.objects.get().status, Order.CONFIRMED)
        self.assertEqual(OrderPayment.objects.count(), 1)

        client.get("/order/payment_failure/")
        # payment process reservation should have been removed now,
        # this does not change anything else though
        self.assertEqual(StockTransaction.objects.count(), 1)
        self.assertEqual(Order.objects.get().status, Order.CHECKOUT)

        self.assertContains(
            self.client.post("/payment/postfinance/ipn/", {}),
            "Missing data",
            status_code=403,
        )

        order = Order.objects.get(pk=1)

        ipn_data = {
            "orderID": "Order-1-1",
            "currency": order.currency,
            "amount": order.balance_remaining,
            "PM": "Postfinance",
            "ACCEPTANCE": "xxx",
            "STATUS": "5",  # Authorized
            "CARDNO": "xxxxxxxxxxxx1111",
            "PAYID": "123456789",
            "NCERROR": "",
            "BRAND": "VISA",
            "SHASIGN": "this-value-is-invalid",
        }

        self.assertContains(
            self.client.post("/payment/postfinance/ipn/", ipn_data),
            "Hash did not validate",
            status_code=403,
        )

        ipn_data["SHASIGN"] = "4b4cf5f9a5f0b54cc119be3696f43f81139232ae"

        self.assertContains(
            self.client.post("/payment/postfinance/ipn/", ipn_data),
            "OK",
            status_code=200,
        )

        order = Order.objects.get(pk=1)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.assertTrue(order.is_paid())
            self.assertEqual(len(w), 1)
            self.assertTrue("Order.is_paid() has been deprecated" in str(w[-1]))
        self.assertTrue(order.status >= Order.PAID)

        self.assertEqual(StockTransaction.objects.count(), 2)

        # Manipulate paid amount
        order.paid -= 10
        order.save()
        self.assertRedirects(client.get("/cart/"), "/confirmation/?confirmed=1")

        self.assertContains(
            client.get("/order/success/"), "<h1>Order has been partially paid.</h1>"
        )

        # Revert manipulation
        order.paid += 10
        order.save()
        self.assertRedirects(client.get("/checkout/"), "/order/success/")

    def test_07_paypal_ipn(self):
        """Test PayPal Instant Payment Notification handler"""
        paypal_ipn_data = {
            "txn_id": "123456789",
            "invoice": "Order-1-1",
            "mc_currency": "CHF",
            "mc_gross": "1234",
            "payment_status": "Completed",
            "last_name": "H\xe5konsen",
        }

        from plata.payment.modules import paypal

        def mock_urlopen(*args, **kwargs):
            qs = parse_qs(args[1])
            self.assertEqual(qs["cmd"][0], "_notify-validate")
            for k, v in paypal_ipn_data.items():
                self.assertEqual("%s" % qs[k][0], v)
            s = BytesIO(b"VERIFIED")
            return s

        paypal.urlopen = mock_urlopen

        product = self.create_product()
        client = self.login()

        product.stock_transactions.create(type=StockTransaction.PURCHASE, change=10)
        client.post(product.get_absolute_url(), {"quantity": 5})

        response = client.post(
            "/confirmation/", {"terms_and_conditions": True, "payment_method": "paypal"}
        )
        self.assertContains(response, "sandbox")

        self.assertEqual(StockTransaction.objects.count(), 2)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderPayment.objects.count(), 1)

        self.assertContains(
            self.client.post("/payment/paypal/ipn/", paypal_ipn_data), "Ok"
        )

        order = Order.objects.get(pk=1)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.assertTrue(order.is_paid())
            self.assertEqual(len(w), 1)
            self.assertTrue("Order.is_paid() has been deprecated" in str(w[-1]))

        self.assertEqual(
            set(
                (
                    StockTransaction.PURCHASE,
                    StockTransaction.SALE,
                    StockTransaction.PAYMENT_PROCESS_RESERVATION,
                )
            ),
            set(StockTransaction.objects.values_list("type", flat=True)),
        )

    def test_08_checkout_preexisting_user(self):
        """Test checkout behavior using existing user without contact"""
        User.objects.create_user("else", "else@example.com", "test")

        User.objects.create_user("test", "test@example.com", "test")
        self.client.login(username="test", password="test")

        p1 = self.create_product(stock=100)
        self.client.post(p1.get_absolute_url(), {"quantity": 5})

        response = self.client.get("/checkout/")
        self.assertContains(response, "Checkout")
        self.assertNotContains(response, "login-username")

        checkout_data = {
            "_checkout": 1,
            "order-billing_company": "BigCorp",
            "order-billing_first_name": "Hans",
            "order-billing_last_name": "Muster",
            "order-billing_address": "Musterstrasse 42",
            "order-billing_zip_code": "8042",
            "order-billing_city": "Beispielstadt",
            "order-billing_country": "CH",
            "order-shipping_same_as_billing": True,
            "order-email": "else@example.com",
            "order-currency": "CHF",
            "order-create_account": True,
        }

        self.assertContains(
            self.client.post("/checkout/", checkout_data),
            "This e-mail address belongs to a different account",
        )

        self.assertEqual(len(mail.outbox), 0)
        checkout_data["order-email"] = "something@example.com"
        self.assertRedirects(
            self.client.post("/checkout/", checkout_data), "/confirmation/"
        )
        self.assertEqual(len(mail.outbox), 1)

        # There should be exactly one contact object now
        contact = Contact.objects.get()
        self.assertEqual(contact.user.orders.count(), 1)
        self.assertEqual(contact.billing_city, "Beispielstadt")

        # User e-mail address is unchanged
        self.assertEqual(contact.user.email, "test@example.com")

    def test_09_checkout_create_user(self):
        """Test checkout behavior without existing user or contact"""
        User.objects.create_user("else", "else@example.com", "test")

        p1 = self.create_product(stock=100)
        self.client.post(p1.get_absolute_url(), {"quantity": 5})

        response = self.client.get("/checkout/")
        self.assertContains(response, "Checkout")
        self.assertContains(response, "login-username")

        checkout_data = {
            "_checkout": 1,
            "order-billing_company": "BigCorp",
            "order-billing_first_name": "Hans",
            "order-billing_last_name": "Muster",
            "order-billing_address": "Musterstrasse 42",
            "order-billing_zip_code": "8042",
            "order-billing_city": "Beispielstadt",
            "order-billing_country": "CH",
            "order-shipping_same_as_billing": True,
            "order-email": "else@example.com",
            "order-currency": "CHF",
            "order-create_account": True,
        }

        self.assertContains(
            self.client.post("/checkout/", checkout_data),
            "This e-mail address might belong to you, but we cannot know for"
            " sure because you are not authenticated yet",
        )

        self.assertEqual(len(mail.outbox), 0)
        checkout_data["order-email"] = "something@example.com"
        self.assertRedirects(
            self.client.post("/checkout/", checkout_data), "/confirmation/"
        )
        self.assertEqual(len(mail.outbox), 1)

        # There should be exactly one contact object now
        contact = Contact.objects.get()
        self.assertEqual(contact.user.orders.count(), 1)
        self.assertEqual(contact.billing_city, "Beispielstadt")

        self.assertEqual(contact.user.email, "something@example.com")

        # New order
        self.client.post(p1.get_absolute_url(), {"quantity": 5})
        response = self.client.get("/checkout/")

        self.assertContains(response, 'value="something@example.com"')
        self.assertContains(response, 'value="Beispielstadt"')

    def test_10_login_in_checkout_preexisting_contact(self):
        """Test checkout behavior using already existing contact and user"""
        Contact.objects.create(
            user=User.objects.create_user(
                "else@example.com", "else@example.com", "test"
            ),
            currency="CHF",
            billing_first_name="Hans",
            billing_last_name="Muster",
        )

        p1 = self.create_product(stock=100)
        self.client.post(p1.get_absolute_url(), {"quantity": 5})

        response = self.client.get("/checkout/")
        self.assertContains(response, "Checkout")
        self.assertContains(response, "login-username")

        self.assertRedirects(
            self.client.post(
                "/checkout/",
                {
                    "_login": 1,
                    "login-username": "else@example.com",
                    "login-password": "test",
                },
            ),
            "/checkout/",
        )

        # Test that the order is still active after logging in
        response = self.client.get("/checkout/")
        self.assertContains(response, 'value="else@example.com"')
        self.assertContains(response, 'value="Muster"')

        checkout_data = {
            "_checkout": 1,
            "order-billing_company": "BigCorp",
            "order-billing_first_name": "Fritz",
            "order-billing_last_name": "Muster",
            "order-billing_address": "Musterstrasse 42",
            "order-billing_zip_code": "8042",
            "order-billing_city": "Beispielstadt",
            "order-billing_country": "CH",
            "order-shipping_same_as_billing": True,
            "order-email": "else@example.com",
            "order-currency": "CHF",
            "order-create_account": True,
        }

        self.assertEqual(len(mail.outbox), 0)
        self.assertRedirects(
            self.client.post("/checkout/", checkout_data), "/confirmation/"
        )
        self.assertEqual(len(mail.outbox), 0)

        contact = Contact.objects.get()
        # First name should be updated in checkout processing
        self.assertEqual(contact.billing_first_name, "Fritz")
        self.assertEqual("%s" % contact, "else@example.com")  # Username

        # Order should be assigned to contact
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(contact.user.orders.count(), 1)

    def test_11_login_in_checkout_create_contact(self):
        """Test checkout using already existing user, but no contact"""
        User.objects.create_user("else@example.com", "else@example.com", "test")

        p1 = self.create_product(stock=100)
        self.client.post(p1.get_absolute_url(), {"quantity": 5})

        response = self.client.get("/checkout/")
        self.assertContains(response, "Checkout")
        self.assertContains(response, "login-username")

        self.assertRedirects(
            self.client.post(
                "/checkout/",
                {
                    "_login": 1,
                    "login-username": "else@example.com",
                    "login-password": "test",
                },
            ),
            "/checkout/",
        )

        checkout_data = {
            "_checkout": 1,
            "order-billing_company": "BigCorp",
            "order-billing_first_name": "Fritz",
            "order-billing_last_name": "Muster",
            "order-billing_address": "Musterstrasse 42",
            "order-billing_zip_code": "8042",
            "order-billing_city": "Beispielstadt",
            "order-billing_country": "CH",
            "order-shipping_same_as_billing": True,
            "order-email": "else@example.com",
            "order-currency": "CHF",
            "order-create_account": True,
        }

        # If order wasn't active after logging in anymore, this would not work
        self.assertRedirects(
            self.client.post("/checkout/", checkout_data), "/confirmation/"
        )

        contact = Contact.objects.get()
        self.assertEqual(contact.billing_first_name, "Fritz")

        # Order should be assigned to contact
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(contact.user.orders.count(), 1)

    def test_12_insufficient_stock(self):
        """Test insufficient stock handling in checkout process"""
        p1 = self.create_product(stock=10)
        self.client.post(p1.get_absolute_url(), {"quantity": 9})

        p1.stock_transactions.create(type=StockTransaction.SALE, change=-5)

        response = self.client.get("/checkout/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            "http://testserver/cart/?e=1" if django.VERSION < (1, 11) else "/cart/?e=1",
        )

        self.assertContains(self.client.get("/cart/"), "Not enough stock available for")

    def test_13_expired_reservation(self):
        """Test payment process reservation expiration"""
        p1 = self.create_product(stock=10)

        self.assertEqual(p1.__class__.objects.get(pk=p1.pk).items_in_stock, 10)

        p1.stock_transactions.create(
            type=StockTransaction.PAYMENT_PROCESS_RESERVATION, change=-7
        )

        # Payment process reservation stock transactions should not modify
        # the items_in_stock field
        self.assertEqual(p1.__class__.objects.get(pk=p1.pk).items_in_stock, 10)

        self.assertEqual(StockTransaction.objects.items_in_stock(p1), 10)
        self.assertEqual(
            StockTransaction.objects.items_in_stock(p1, include_reservations=True), 3
        )

        StockTransaction.objects.update(created=timezone.now() - timedelta(minutes=10))
        self.assertEqual(StockTransaction.objects.items_in_stock(p1), 10)
        self.assertEqual(
            StockTransaction.objects.items_in_stock(p1, include_reservations=True), 3
        )

        StockTransaction.objects.update(created=timezone.now() - timedelta(minutes=20))
        self.assertEqual(
            StockTransaction.objects.items_in_stock(p1, include_reservations=True), 10
        )
        self.assertEqual(StockTransaction.objects.items_in_stock(p1), 10)

        order = self.create_order()
        order.modify_item(p1, relative=5)
        order.validate(order.VALIDATE_ALL)

        StockTransaction.objects.update(created=timezone.now() - timedelta(minutes=10))
        self.assertRaises(ValidationError, order.validate, order.VALIDATE_ALL)

    def test_14_remaining_discount(self):
        """Test that a new discount is created when there is an amount
        remaining"""
        p1 = self.create_product(stock=10)
        client = self.login()
        client.post(p1.get_absolute_url(), {"quantity": 5})

        discount = Discount.objects.create(
            name="Testname",
            type=Discount.AMOUNT_VOUCHER_INCL_TAX,
            value=1000,
            config='{"all":{}}',
            tax_class=self.tax_class,
            currency="CHF",
        )

        self.assertRedirects(
            client.post("/discounts/", {"code": discount.code, "proceed": "True"}),
            "/confirmation/",
        )

        self.assertRedirects(
            client.post(
                "/confirmation/",
                {"terms_and_conditions": True, "payment_method": "cod"},
            ),
            "/order/success/",
        )

        self.assertEqual(Discount.objects.count(), 2)

        order = Order.objects.get()
        new_discount = Discount.objects.exclude(code=discount.code).get()

        self.assertAlmostEqual(
            discount.value - sum(item.subtotal for item in order.items.all()),
            new_discount.value * (1 + self.tax_class.rate / 100),
        )

        client.get("/order/new/")

        client.post(p1.get_absolute_url(), {"quantity": 1})
        self.assertRedirects(
            client.post("/discounts/", {"code": new_discount.code, "proceed": "True"}),
            "/confirmation/",
        )

        self.assertRedirects(
            client.post(
                "/confirmation/",
                {"terms_and_conditions": True, "payment_method": "cod"},
            ),
            "/order/success/",
        )

        client.get("/order/new/")
        client.get("/order/new/")  # Shouldn't do anything the second time
        client.post(p1.get_absolute_url(), {"quantity": 1})
        self.assertContains(
            client.post("/discounts/", {"code": new_discount.code, "proceed": "True"}),
            "Allowed uses for this discount has already been reached.",
        )

        # Stock transactions must be created for orders which are paid from
        # the start. 10 purchase, -5 sale, -1 sale
        self.assertEqual(StockTransaction.objects.count(), 3)
        p1 = Product.objects.get(pk=p1.pk)
        self.assertEqual(p1.items_in_stock, 4)
