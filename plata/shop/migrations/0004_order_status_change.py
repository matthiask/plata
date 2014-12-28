# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0003_default_currencies_change'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.PositiveIntegerField(default=10, verbose_name='status', choices=[(10, 'Is a cart'), (20, 'Checkout process started'), (30, 'Order has been confirmed'), (35, 'Order is pending payment'), (40, 'Order has been paid'), (50, 'Order has been completed')]),
        ),
        migrations.AlterField(
            model_name='orderstatus',
            name='status',
            field=models.PositiveIntegerField(max_length=20, verbose_name='status', choices=[(10, 'Is a cart'), (20, 'Checkout process started'), (30, 'Order has been confirmed'), (35, 'Order is pending payment'), (40, 'Order has been paid'), (50, 'Order has been completed')]),
        ),
    ]
