from datetime import date
from decimal import Decimal
import random

from django.test import TestCase
from django.contrib.auth.models import AnonymousUser

from plata import plata_settings
from plata.contact.models import Contact
from plata.product.models import TaxClass, Product, ProductVariation, Discount,\
    ProductPrice, OptionGroup, Option
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

        product.create_variations()

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
