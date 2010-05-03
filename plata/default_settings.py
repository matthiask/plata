from django.conf import settings

# Are prices shown with tax included or not?
PLATA_PRICE_INCLUDES_TAX = getattr(settings, 'PLATA_PRICE_INCLUDES_TAX', True)

PLATA_PRODUCT_MODULE = getattr(settings, 'PLATA_PRODUCT_MODULE', 'plata.product.simple.models')
