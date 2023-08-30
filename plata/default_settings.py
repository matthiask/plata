from decimal import Decimal

from django.conf import settings
from django.utils.translation import gettext_lazy as _


#: Are prices shown with tax included or not? (Defaults to ``True``)
#: Please note that this setting is purely presentational and has no
#: influence on the values stored in the database.
PLATA_PRICE_INCLUDES_TAX = getattr(settings, "PLATA_PRICE_INCLUDES_TAX", True)

#: List of order processors
#:
#: Plata does not check whether the selection makes any sense. This is your
#: responsibility.
PLATA_ORDER_PROCESSORS = getattr(
    settings,
    "PLATA_ORDER_PROCESSORS",
    [
        "plata.shop.processors.InitializeOrderProcessor",
        "plata.shop.processors.DiscountProcessor",
        "plata.shop.processors.TaxProcessor",
        "plata.shop.processors.MeansOfPaymentDiscountProcessor",
        "plata.shop.processors.ItemSummationProcessor",
        "plata.shop.processors.ZeroShippingProcessor",
        "plata.shop.processors.OrderSummationProcessor",
    ],
)

#: Activated payment modules
PLATA_PAYMENT_MODULES = getattr(
    settings,
    "PLATA_PAYMENT_MODULES",
    [
        "plata.payment.modules.cod.PaymentProcessor",
        "plata.payment.modules.paypal.PaymentProcessor",
    ],
)

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
PLATA_PAYMENT_MODULE_NAMES = getattr(settings, "PLATA_PAYMENT_MODULE_NAMES", {})

#: ``FixedAmountShippingProcessor`` example configuration
#:
#: The cost must be specified with tax included.
PLATA_SHIPPING_FIXEDAMOUNT = getattr(
    settings,
    "PLATA_SHIPPING_FIXEDAMOUNT",
    {"cost": Decimal("8.00"), "tax": Decimal("7.6")},
)

#: ``shipping.Postage`` configuration
#: change this if you insist in obsolete non-metric units
PLATA_SHIPPING_WEIGHT_UNIT = "g"
PLATA_SHIPPING_LENGTH_UNIT = "mm"

#: Stationery for invoice and packing slip PDF generation
PLATA_REPORTING_STATIONERY = getattr(
    settings, "PLATA_REPORTING_STATIONERY", "pdfdocument.elements.ExampleStationery"
)

#: PDF address line
PLATA_REPORTING_ADDRESSLINE = getattr(settings, "PLATA_REPORTING_ADDRESSLINE", "")

#: Transactional stock tracking
#:
#: ``'plata.product.stock'`` has to be included in ``INSTALLED_APPS`` for
#: this to work.
PLATA_STOCK_TRACKING = getattr(settings, "PLATA_STOCK_TRACKING", False)
PLATA_STOCK_TRACKING_MODEL = getattr(
    settings, "PLATA_STOCK_TRACKING_MODEL", "stock.StockTransaction"
)

#: All available currencies. Use ISO 4217 currency codes in this list only.
CURRENCIES = getattr(settings, "CURRENCIES", ("CHF", "EUR", "USD", "CAD"))
#: If you use currencies that don't have a minor unit (zero-decimal currencies)
#: At the moment only relevant to Stripe payments.
CURRENCIES_WITHOUT_CENTS = getattr(settings, "CURRENCIES_WITHOUT_CENTS", ("JPY", "KRW"))

#: Target of order item product foreign key (Defaults to ``'product.Product'``)
PLATA_SHOP_PRODUCT = getattr(settings, "PLATA_SHOP_PRODUCT", "product.Product")

#: Since ZIP code is far from universal, and more an L10N than I18N issue:
PLATA_ZIP_CODE_LABEL = getattr(settings, "PLATA_ZIP_CODE_LABEL", _("ZIP code"))

#: Custom font for PDF generation
PLATA_PDF_FONT_NAME = getattr(settings, "PLATA_PDF_FONT_NAME", "")
PLATA_PDF_FONT_PATH = getattr(settings, "PLATA_PDF_FONT_PATH", "")
PLATA_PDF_FONT_BOLD_NAME = getattr(settings, "PLATA_PDF_FONT_BOLD_NAME", "")
PLATA_PDF_FONT_BOLD_PATH = getattr(settings, "PLATA_PDF_FONT_BOLD_PATH", "")
