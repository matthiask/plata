from django.db import models
from django.utils.functional import curry
from django.utils.translation import ugettext_lazy as _


CURRENCIES = ('CHF', 'EUR', 'USD')


CurrencyField = curry(models.CharField, _('currency'), max_length=3, choices=zip(
    CURRENCIES, CURRENCIES))
