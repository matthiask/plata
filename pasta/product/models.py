from django.db import models
from django.utils.translation import ugettext_lazy as _


class Product(models.Model):
    name = models.CharField(max_length=100)
    unit_price = models.DecimalField(_('unit price'), max_digits=18, decimal_places=10)

    class Meta:
        pass

    def __unicode__(self):
        return self.name
