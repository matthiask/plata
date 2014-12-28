# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0002_orderpayment_transaction_fee'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='currency',
            field=models.CharField(max_length=3, verbose_name='currency', choices=[(b'SEK', b'SEK'), (b'EUR', b'EUR'), (b'NOK', b'NOK'), (b'DKK', b'DKK')]),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='currency',
            field=models.CharField(max_length=3, verbose_name='currency', choices=[(b'SEK', b'SEK'), (b'EUR', b'EUR'), (b'NOK', b'NOK'), (b'DKK', b'DKK')]),
        ),
        migrations.AlterField(
            model_name='orderpayment',
            name='currency',
            field=models.CharField(max_length=3, verbose_name='currency', choices=[(b'SEK', b'SEK'), (b'EUR', b'EUR'), (b'NOK', b'NOK'), (b'DKK', b'DKK')]),
        ),
    ]
