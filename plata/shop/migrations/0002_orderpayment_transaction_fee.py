# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderpayment',
            name='transaction_fee',
            field=models.DecimalField(decimal_places=2, max_digits=10, blank=True, help_text='Fee charged by the payment processor.', null=True, verbose_name='transaction fee'),
            preserve_default=True,
        ),
    ]
