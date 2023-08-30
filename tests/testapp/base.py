from decimal import Decimal

from django.contrib.auth.models import AnonymousUser
from django.test import Client, TestCase

import plata
from plata.contact.models import Contact
from plata.product.stock.models import StockTransaction
from plata.shop import notifications, signals
from plata.shop.models import Order, OrderItem, TaxClass


try:  # pragma: no cover
    from django.contrib.auth import get_user_model

    User = get_user_model()
except ImportError:
    from django.contrib.auth.models import User


signals.contact_created.connect(
    notifications.ContactCreatedHandler(always_bcc=["shop@example.com"]), weak=False
)
signals.order_paid.connect(
    notifications.SendInvoiceHandler(always_bcc=["shop@example.com"]), weak=False
)
signals.order_paid.connect(
    notifications.SendPackingSlipHandler(
        always_to=["shipping@example.com"], always_bcc=["shop@example.com"]
    ),
    weak=False,
)


class Empty:
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


PRODUCTION_CREATION_COUNTER = 0


class PlataTest(TestCase):
    def assertRaisesWithCode(self, exception, fn, code):
        try:
            fn()
        except exception as e:
            if e.code == code:
                return True
            raise
        raise Exception(f"{fn} did not raise {exception}")

    def create_contact(self):
        return Contact.objects.create(
            billing_company="BigCorp",
            billing_first_name="Hans",
            billing_last_name="Muster",
            billing_address="Musterstrasse 42",
            billing_zip_code="8042",
            billing_city="Beispielstadt",
            billing_country="CH",
            shipping_same_as_billing=True,
            currency="CHF",
            user=User.objects.create_user("hans", "hans", "hans"),
        )

    def create_order(self, contact=None):
        contact = contact or self.create_contact()

        return Order.objects.create(
            user=contact.user if contact else None, currency="CHF"
        )

    def create_orderitem(self, product, order):
        item = OrderItem(
            product=product,
            order=order,
            quantity=1,
            _unit_price=0,
            _unit_tax=0,
            tax_rate=0,
        )
        product.handle_order_item(item)
        return item

    def create_tax_classes(self):
        self.tax_class, created = TaxClass.objects.get_or_create(
            name="Standard Swiss Tax Rate", rate=Decimal("7.60")
        )

        self.tax_class_germany, created = TaxClass.objects.get_or_create(
            name="Umsatzsteuer (Germany)", rate=Decimal("19.60")
        )

        self.tax_class_something, created = TaxClass.objects.get_or_create(
            name="Some tax rate", rate=Decimal("12.50")
        )

        return self.tax_class, self.tax_class_germany, self.tax_class_something

    def create_product(self, stock=0):
        global PRODUCTION_CREATION_COUNTER
        PRODUCTION_CREATION_COUNTER += 1

        tax_class, tax_class_germany, tax_class_something = self.create_tax_classes()

        Product = plata.product_model()
        product = Product.objects.create(
            name="Test Product %s" % PRODUCTION_CREATION_COUNTER
        )

        if stock:
            product.stock_transactions.create(
                type=StockTransaction.PURCHASE, change=stock
            )

        # An old price in CHF which should not influence the rest of the tests
        product.prices.create(
            currency="CHF",
            tax_class=tax_class,
            _unit_price=Decimal("99.90"),
            tax_included=True,
        )

        product.prices.create(
            currency="CHF",
            tax_class=tax_class,
            _unit_price=Decimal("199.90"),
            tax_included=True,
            # valid_from=date(2000, 1, 1),
            # valid_until=date(2001, 1, 1),
        )

        product.prices.create(
            currency="CHF",
            tax_class=tax_class,
            _unit_price=Decimal("299.90"),
            tax_included=True,
            # valid_from=date(2000, 1, 1),
        )

        product.prices.create(
            currency="CHF",
            tax_class=tax_class,
            _unit_price=Decimal("299.90"),
            tax_included=True,
            # valid_from=date(2000, 7, 1),
            # is_sale=True,
        )

        product.prices.create(
            currency="CHF",
            tax_class=tax_class,
            _unit_price=Decimal("79.90"),
            tax_included=True,
            # is_sale=True,
        )

        product.prices.create(
            currency="EUR",
            tax_class=tax_class_germany,
            _unit_price=Decimal("49.90"),
            tax_included=True,
        )

        product.prices.create(
            currency="CAD",
            tax_class=tax_class_something,
            _unit_price=Decimal("65.00"),
            tax_included=False,
        )

        """
        # A few prices which are not yet (or no more) active
        product.prices.create(
            currency='CHF',
            tax_class=tax_class,
            _unit_price=Decimal('110.00'),
            tax_included=True,
            #is_active=False,
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
        """

        return product

    def login(self):
        User.objects.create_user("test", "test@example.com", "testing")
        client = Client()
        client.login(username="test", password="testing")
        return client
