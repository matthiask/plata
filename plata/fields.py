from django.db import models
from django.utils.functional import curry
from django.utils.translation import ugettext_lazy as _

import plata


#: Field offering all defined currencies
CurrencyField = curry(models.CharField, _('currency'), max_length=3, choices=zip(
    plata.settings.CURRENCIES, plata.settings.CURRENCIES))
