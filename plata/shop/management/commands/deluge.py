# ------------------------------------------------------------------------
# coding=utf-8
# $Id$
# ------------------------------------------------------------------------

from decimal import Decimal
import random

from django.contrib.auth.models import User
from django.core.management.base import NoArgsCommand
from django.db import transaction

from plata.contact.models import Contact
from plata.product.models import Category, Product, Discount, TaxClass
from plata.shop.models import Order


class Command(NoArgsCommand):
    help = "Create many, many, many objects inside the shop."

    def handle_noargs(self, **options):
        categories = []

        u = User.objects.create_user('admin', 'admin@example.com', 'password')
        u.is_staff = True
        u.is_superuser = True
        u.save()

        tax_class = TaxClass.objects.create(
            name='Swiss tax',
            rate=Decimal('7.6'),
            )

        for i in range(10):
            r = random.randint(0, 10000000)
            categories.append(Category.objects.create(
                name='Category %s - %s' % (i, r),
                slug='cat%s' % r,
                is_active=True,
                ordering=i,
                ))

        for i in range(1000):
            r = random.randint(0, 10000000)
            p = Product.objects.create(
                is_active=True,
                name='Product %s - %s' % (i, r),
                slug='prod%s' % r,
                ordering=i,
                )

            p.categories = random.sample(categories, random.randint(1, 10))

            p.prices.create(
                currency='CHF',
                _unit_price=Decimal(random.randint(100, 100000)) / 100,
                tax_included=True,
                is_active=True,
                tax_class=tax_class)

            p.create_variations()
