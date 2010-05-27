from django.conf import settings

# Are prices shown with tax included or not?
PLATA_PRICE_INCLUDES_TAX = getattr(settings, 'PLATA_PRICE_INCLUDES_TAX', True)

PLATA_ORDER_PROCESSORS = getattr(settings, 'PLATA_ORDER_PROCESSORS', [
    'plata.shop.processors.InitializeOrderProcessor',
    'plata.shop.processors.DiscountProcessor',
    'plata.shop.processors.TaxProcessor',
    'plata.shop.processors.ItemSummationProcessor',
    'plata.shop.processors.ShippingProcessor',
    'plata.shop.processors.OrderSummationProcessor',
    ])

PLATA_PAYMENT_MODULES = getattr(settings, 'PLATA_PAYMENT_MODULES', [
    'plata.payment.modules.cod.PaymentProcessor',
    'plata.payment.modules.postfinance.PaymentProcessor',
    'plata.payment.modules.paypal.PaymentProcessor',
    ])
