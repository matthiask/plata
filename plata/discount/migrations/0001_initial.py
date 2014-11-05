# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf import settings

from django.db import models, migrations
import datetime
import plata.fields
import plata.discount.models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppliedDiscount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='name')),
                ('type', models.PositiveIntegerField(verbose_name='type', choices=[(10, 'amount voucher excl. tax (reduces total tax on order)'), (20, 'amount voucher incl. tax (reduces total tax on order)'), (30, 'percentage voucher (reduces total tax on order)'), (40, 'means of payment (does not change total tax on order)')])),
                ('value', models.DecimalField(verbose_name='value', max_digits=18, decimal_places=10)),
                ('currency', models.CharField(choices=[(b'CHF', b'CHF'), (b'EUR', b'EUR'), (b'USD', b'USD'), (b'CAD', b'CAD')], max_length=3, blank=True, help_text='Only required for amount discounts.', null=True, verbose_name='currency')),
                ('config', plata.fields.JSONField(help_text='If you edit this field directly, changes below will be ignored.', verbose_name='configuration', blank=True)),
                ('code', models.CharField(max_length=30, verbose_name='code')),
                ('remaining', models.DecimalField(default=0, help_text='Discount amount excl. tax remaining after discount has been applied.', verbose_name='remaining', max_digits=18, decimal_places=10)),
                ('order', models.ForeignKey(related_name=b'applied_discounts', verbose_name='order', to='shop.Order')),
                ('tax_class', models.ForeignKey(blank=True, to='shop.TaxClass', help_text='Only required for amount discounts incl. tax.', null=True, verbose_name='tax class')),
            ],
            options={
                'ordering': ['type', 'name'],
                'verbose_name': 'applied discount',
                'verbose_name_plural': 'applied discounts',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Discount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='name')),
                ('type', models.PositiveIntegerField(verbose_name='type', choices=[(10, 'amount voucher excl. tax (reduces total tax on order)'), (20, 'amount voucher incl. tax (reduces total tax on order)'), (30, 'percentage voucher (reduces total tax on order)'), (40, 'means of payment (does not change total tax on order)')])),
                ('value', models.DecimalField(verbose_name='value', max_digits=18, decimal_places=10)),
                ('currency', models.CharField(choices=[(b'CHF', b'CHF'), (b'EUR', b'EUR'), (b'USD', b'USD'), (b'CAD', b'CAD')], max_length=3, blank=True, help_text='Only required for amount discounts.', null=True, verbose_name='currency')),
                ('config', plata.fields.JSONField(help_text='If you edit this field directly, changes below will be ignored.', verbose_name='configuration', blank=True)),
                ('code', models.CharField(default=plata.discount.models.generate_random_code, unique=True, max_length=30, verbose_name='code')),
                ('is_active', models.BooleanField(default=True, verbose_name='is active')),
                ('valid_from', models.DateField(default=datetime.date.today, verbose_name='valid from')),
                ('valid_until', models.DateField(null=True, verbose_name='valid until', blank=True)),
                ('allowed_uses', models.IntegerField(help_text='Leave empty if there is no limit on the number of uses of this discount.', null=True, verbose_name='number of allowed uses', blank=True)),
                ('used', models.IntegerField(default=0, verbose_name='number of times already used')),
                ('tax_class', models.ForeignKey(blank=True, to='shop.TaxClass', help_text='Only required for amount discounts incl. tax.', null=True, verbose_name='tax class')),
            ],
            options={
                'verbose_name': 'discount',
                'verbose_name_plural': 'discounts',
            },
            bases=(models.Model,),
        ),
    ]
