"""
Note: The E-Mail configuration (PLATA_ALWAYS_BCC, PLATA_ORDER_BCC and
PLATA_SHIPPING_INFO) is obscure and not very flexible and will be
reworked.
"""

from decimal import Decimal

from django.conf import settings

#: Are prices shown with tax included or not?
PLATA_PRICE_INCLUDES_TAX = getattr(settings, 'PLATA_PRICE_INCLUDES_TAX', True)

#: List of order processors
PLATA_ORDER_PROCESSORS = getattr(settings, 'PLATA_ORDER_PROCESSORS', [
    'plata.shop.processors.InitializeOrderProcessor',
    'plata.shop.processors.DiscountProcessor',
    'plata.shop.processors.TaxProcessor',
    'plata.shop.processors.ItemSummationProcessor',
    'plata.shop.processors.ZeroShippingProcessor',
    'plata.shop.processors.OrderSummationProcessor',
    ])

#: Activated payment modules
PLATA_PAYMENT_MODULES = getattr(settings, 'PLATA_PAYMENT_MODULES', [
    'plata.payment.modules.cod.PaymentProcessor',
    'plata.payment.modules.postfinance.PaymentProcessor',
    'plata.payment.modules.paypal.PaymentProcessor',
    ])

#: Override payment module names without modifying the payment module code
PLATA_PAYMENT_MODULE_NAMES = getattr(settings, 'PLATA_PAYMENT_MODULE_NAMES', {})

#: ``FixedAmountShippingProcessor`` example configuration
PLATA_SHIPPING_FIXEDAMOUNT = getattr(settings, 'PLATA_SHIPPING_FIXEDAMOUNT', {
    'cost': Decimal('8.00'),
    'tax': Decimal('7.6'),
    })

#: Stationery for invoice and packing slip PDF generation
PLATA_REPORTING_STATIONERY = getattr(settings, 'PLATA_REPORTING_STATIONERY',
    'pdfdocument.elements.ExampleStationery')

#: PDF address line
PLATA_REPORTING_ADDRESSLINE = getattr(settings, 'PLATA_REPORTING_ADDRESSLINE', '')

#: Always BCC those people when sending out invoice and packing slip emails
PLATA_ALWAYS_BCC = getattr(settings, 'PLATA_ALWAYS_BCC',
    [email for name, email in settings.ADMINS])

#: Always BCC these people on successful orders
PLATA_ORDER_BCC = getattr(settings, 'PLATA_ORDER_BCC',
    [email for name, email in settings.MANAGERS])

#: Send shipping information to these people
PLATA_SHIPPING_INFO = getattr(settings, 'PLATA_SHIPPING_INFO', PLATA_ORDER_BCC)

CURRENCIES = getattr(settings, 'CURRENCIES', ('CHF', 'EUR', 'USD', 'CAD'))
