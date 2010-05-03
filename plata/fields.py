from django.db import models
from django.utils.functional import curry
from django.utils.translation import ugettext_lazy as _


CurrencyField = curry(models.CharField, _('currency'), max_length=3, choices=(
    ('CHF', 'CHF'),
    ('EUR', 'EUR'),
    ('USD', 'USD'),
    ))
