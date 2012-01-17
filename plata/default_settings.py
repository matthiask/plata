from decimal import Decimal

from django.conf import settings

#: Are prices shown with tax included or not? (Defaults to ``True``)
PLATA_PRICE_INCLUDES_TAX = getattr(settings, 'PLATA_PRICE_INCLUDES_TAX', True)

#: List of order processors
#:
#: Plata does not check whether the selection makes any sense. This is your
#: responsability.
PLATA_ORDER_PROCESSORS = getattr(settings, 'PLATA_ORDER_PROCESSORS', [
    'plata.shop.processors.InitializeOrderProcessor',
    'plata.shop.processors.DiscountProcessor',
    'plata.shop.processors.TaxProcessor',
    'plata.shop.processors.MeansOfPaymentDiscountProcessor',
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
#:
#: The key in this dictionary should use the ``key`` variable of the
#: respective payment module.
#:
#: Example::
#:
#:     PLATA_PAYMENT_MODULE_NAMES = {
#:         'paypal': 'PayPal and Credit Cards',
#:     }
PLATA_PAYMENT_MODULE_NAMES = getattr(settings, 'PLATA_PAYMENT_MODULE_NAMES', {})

#: ``FixedAmountShippingProcessor`` example configuration
#:
#: The cost must be specified with tax included.
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
#:
#: ``'plata.product.stock'`` has to be included in ``INSTALLED_APPS`` for this
#: to work.
PLATA_STOCK_TRACKING = getattr(settings, 'PLATA_STOCK_TRACKING', False)

#: All available currencies. Use ISO 4217 currency codes in this list only.
CURRENCIES = getattr(settings, 'CURRENCIES', ('CHF', 'EUR', 'USD', 'CAD'))

#: Target of order item product foreign key (Defaults to ``'product.Product'``)
PLATA_SHOP_PRODUCT = getattr(settings, 'PLATA_SHOP_PRODUCT', 'product.Product')
