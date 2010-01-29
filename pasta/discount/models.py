from django.db import models
from django.utils.translation import ugettext_lazy as _


class DiscountProcessor(object):
    def eligible_products(self):
        return Product.objects.all()



class AutomaticDiscount(DiscountProcessor):
    pass


class PercentageDiscount(DiscountProcessor):
    pass


class AmountDiscount(DiscountProcessor):
    pass

