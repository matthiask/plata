from decimal import Decimal

from django.conf import settings

# Are prices shown with tax included or not?
PLATA_PRICE_INCLUDES_TAX = getattr(settings, 'PLATA_PRICE_INCLUDES_TAX', True)

PLATA_ORDER_PROCESSORS = getattr(settings, 'PLATA_ORDER_PROCESSORS', [
    'plata.shop.processors.InitializeOrderProcessor',
    'plata.shop.processors.DiscountProcessor',
    'plata.shop.processors.TaxProcessor',
    'plata.shop.processors.ItemSummationProcessor',
    'plata.shop.processors.ZeroShippingProcessor',
    'plata.shop.processors.OrderSummationProcessor',
    ])

PLATA_PAYMENT_MODULES = getattr(settings, 'PLATA_PAYMENT_MODULES', [
    'plata.payment.modules.cod.PaymentProcessor',
    'plata.payment.modules.postfinance.PaymentProcessor',
    'plata.payment.modules.paypal.PaymentProcessor',
    ])

PLATA_PAYMENT_MODULE_NAMES = getattr(settings, 'PLATA_PAYMENT_MODULE_NAMES', {})

PLATA_SHIPPING_FIXEDAMOUNT = getattr(settings, 'PLATA_SHIPPING_FIXEDAMOUNT', {
    'cost': Decimal('8.00'),
    'tax': Decimal('7.6'),
    })

PLATA_REPORTING_STATIONERY = getattr(settings, 'PLATA_REPORTING_STATIONERY',
    'pdfdocument.elements.ExampleStationery')
PLATA_REPORTING_ADDRESSLINE = getattr(settings, 'PLATA_REPORTING_ADDRESSLINE', '')

PLATA_ALWAYS_BCC = getattr(settings, 'PLATA_ALWAYS_BCC',
    [email for name, email in settings.ADMINS])
PLATA_ORDER_BCC = getattr(settings, 'PLATA_ORDER_BCC',
    [email for name, email in settings.MANAGERS])

CURRENCIES = getattr(settings, 'CURRENCIES', ('CHF', 'EUR', 'USD'))
