# Django settings for testapp project.

import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = ()

MANAGERS = ADMINS

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "test.db"}}

TIME_ZONE = "America/Chicago"
LANGUAGE_CODE = "en-us"
SITE_ID = 1
USE_I18N = True
USE_L10N = True
USE_TZ = True
MEDIA_ROOT = ""
MEDIA_URL = ""
STATIC_ROOT = ""
STATIC_URL = "/static/"
STATICFILES_DIRS = ()
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)
SECRET_KEY = "58_c#ha*osgvo(809%#@kf!4_ab((a4tl6ypa_0i_teh&amp;%dul$"
MIDDLEWARE = MIDDLEWARE_CLASSES = (
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(os.path.dirname(__file__), "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "plata.context_processors.plata_context",
            ]
        },
    }
]

ROOT_URLCONF = "testapp.urls"
WSGI_APPLICATION = "testapp.wsgi.application"

INSTALLED_APPS = (
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "testapp",
    "plata",
    "plata.contact",  # Not strictly required (contact model can be exchanged)
    "plata.discount",
    "plata.payment",
    "plata.product",  # Does nothing
    "plata.product.stock",  # Accurate stock tracking, not required
    "plata.shop",
)

PLATA_SHOP_PRODUCT = "testapp.Product"
PLATA_STOCK_TRACKING = True
POSTFINANCE = {
    "PSPID": "plataTEST",
    "SHA1_IN": "plataSHA1_IN",
    "SHA1_OUT": "plataSHA1_OUT",
    "LIVE": False,
}

PAYPAL = {"BUSINESS": "example@paypal.com", "LIVE": False}

PLATA_PAYMENT_MODULES = [
    "plata.payment.modules.cod.PaymentProcessor",
    "plata.payment.modules.postfinance.PaymentProcessor",
    "plata.payment.modules.paypal.PaymentProcessor",
]
PLATA_PRICE_INCLUDES_TAX = True
