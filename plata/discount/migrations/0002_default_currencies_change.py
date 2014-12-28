# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('discount', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applieddiscount',
            name='currency',
            field=models.CharField(choices=[(b'SEK', b'SEK'), (b'EUR', b'EUR'), (b'NOK', b'NOK'), (b'DKK', b'DKK')], max_length=3, blank=True, help_text='Only required for amount discounts.', null=True, verbose_name='currency'),
        ),
        migrations.AlterField(
            model_name='discount',
            name='currency',
            field=models.CharField(choices=[(b'SEK', b'SEK'), (b'EUR', b'EUR'), (b'NOK', b'NOK'), (b'DKK', b'DKK')], max_length=3, blank=True, help_text='Only required for amount discounts.', null=True, verbose_name='currency'),
        ),
    ]
