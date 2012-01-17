from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import AnonymousUser, User

import plata
from plata.contact.models import Contact
from plata.product.stock.models import StockTransaction
from plata.shop import notifications, signals
from plata.shop.models import TaxClass, Order


signals.contact_created.connect(
    notifications.ContactCreatedHandler(always_bcc=['shop@example.com']),
    weak=False)
signals.order_completed.connect(
    notifications.SendInvoiceHandler(always_bcc=['shop@example.com']),
    weak=False)
signals.order_completed.connect(
    notifications.SendPackingSlipHandler(
        always_to=['shipping@example.com'],
        always_bcc=['shop@example.com']),
    weak=False)


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


PRODUCTION_CREATION_COUNTER = 0

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
        plata.settings.PLATA_PRICE_INCLUDES_TAX = True

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
            user=User.objects.create_user('hans', 'hans', 'hans'),
            )

    def create_order(self, contact=None):
        contact = contact or self.create_contact()

        return Order.objects.create(
            user=contact.user if contact else None,
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


    def create_product(self, stock=0):
        global PRODUCTION_CREATION_COUNTER
        PRODUCTION_CREATION_COUNTER += 1

        tax_class, tax_class_germany, tax_class_something = self.create_tax_classes()

        Product = plata.product_model()
        product = Product.objects.create(
            name='Test Product %s' % PRODUCTION_CREATION_COUNTER,
            )

        if stock:
            product.stock_transactions.create(
                type=StockTransaction.PURCHASE,
                change=stock,
                )

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
            _unit_price=Decimal('199.90'),
            tax_included=True,
            #valid_from=date(2000, 1, 1),
            #valid_until=date(2001, 1, 1),
            )

        product.prices.create(
            currency='CHF',
            tax_class=tax_class,
            _unit_price=Decimal('299.90'),
            tax_included=True,
            #valid_from=date(2000, 1, 1),
            )

        product.prices.create(
            currency='CHF',
            tax_class=tax_class,
            _unit_price=Decimal('299.90'),
            tax_included=True,
            #valid_from=date(2000, 7, 1),
            #is_sale=True,
            )

        product.prices.create(
            currency='CHF',
            tax_class=tax_class,
            _unit_price=Decimal('79.90'),
            tax_included=True,
            #is_sale=True,
            )

        product.prices.create(
            currency='EUR',
            tax_class=tax_class_germany,
            _unit_price=Decimal('49.90'),
            tax_included=True,
            )

        product.prices.create(
            currency='CAD',
            tax_class=tax_class_something,
            _unit_price=Decimal('65.00'),
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
