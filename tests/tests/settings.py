# Django settings for tests project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test.db',
    }
}

TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
USE_L10N = True
USE_TZ = False
MEDIA_ROOT = ''
MEDIA_URL = ''
STATIC_ROOT = ''
STATIC_URL = '/static/'
STATICFILES_DIRS = (
)
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
SECRET_KEY = '58_c#ha*osgvo(809%#@kf!4_ab((a4tl6ypa_0i_teh&amp;%dul$'
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)
MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'tests.urls'
WSGI_APPLICATION = 'tests.wsgi.application'

TEMPLATE_DIRS = (
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',

    'tests',
    'plata',
    'plata.contact', # Not strictly required (contact model can be exchanged)
    'plata.discount',
    'plata.payment',
    'plata.product', # Does nothing
    'plata.product.stock', # Accurate stock tracking, not required
    'plata.shop',
)

PLATA_SHOP_PRODUCT = 'tests.Product'
PLATA_STOCK_TRACKING = True
POSTFINANCE = {
    'PSPID': 'plataTEST',
    'SHA1_IN': 'plataSHA1_IN',
    'SHA1_OUT': 'plataSHA1_OUT',
    'LIVE': False,
    }

PAYPAL = {
    'BUSINESS': 'example@paypal.com',
    'LIVE': False,
    }

TEST_RUNNER = 'tests.test_runner.CoverageRunner'
COVERAGE_MODULES = [
    'plata',
    'plata.compat',
    'plata.contact.admin',
    'plata.contact.models',
    'plata.context_processors',
    'plata.default_settings',
    'plata.discount.admin',
    'plata.discount.models',
    'plata.fields',
    'plata.models',
    'plata.payment.modules.base',
    'plata.payment.modules.cod',
    'plata.payment.modules.paypal',
    'plata.payment.modules.postfinance',
    'plata.product.models',
    'plata.product.stock.admin',
    'plata.product.stock.models',
    'plata.reporting.order',
    'plata.reporting.product',
    'plata.reporting.urls',
    'plata.reporting.views',
    'plata.shop.admin',
    'plata.shop.models',
    'plata.shop.notifications',
    'plata.shop.processors',
    'plata.shop.signals',
    'plata.shop.templatetags.plata_tags',
    'plata.shop.views',
    #'plata.tests.admin',
    #'plata.tests.base',
    #'plata.tests.models',
    #'plata.tests.views',
    'plata.utils',
]
