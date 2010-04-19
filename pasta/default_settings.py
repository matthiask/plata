from django.conf import settings

# Are prices shown with tax included or not?
PASTA_PRICE_INCLUDES_TAX = getattr(settings, 'PASTA_PRICE_INCLUDES_TAX', True)

# Are discounts applied before tax or not?
PASTA_DISCOUNT_INCLUDES_TAX = getattr(settings, 'PASTA_DISCOUNT_INCLUDES_TAX', True)
