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

#: Transactional stock tracking
PLATA_STOCK_TRACKING = getattr(settings, 'PLATA_STOCK_TRACKING', False)

CURRENCIES = getattr(settings, 'CURRENCIES', ('CHF', 'EUR', 'USD', 'CAD'))

#: Target of order item product foreign key
PLATA_SHOP_PRODUCT = getattr(settings, 'PLATA_SHOP_PRODUCT', 'product.Product')

#: Should the options module product use FeinCMS?
PLATA_PRODUCT_OPTIONS_FEINCMS = getattr(settings, 'PLATA_PRODUCT_OPTIONS_FEINCMS', False)
