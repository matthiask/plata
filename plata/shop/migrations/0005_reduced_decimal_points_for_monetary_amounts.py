# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0004_order_status_change'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='items_discount',
            field=models.DecimalField(default=Decimal('0.00'), verbose_name='items discount', max_digits=18, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='order',
            name='items_subtotal',
            field=models.DecimalField(default=Decimal('0.00'), verbose_name='subtotal', max_digits=18, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='order',
            name='items_tax',
            field=models.DecimalField(default=Decimal('0.00'), verbose_name='items tax', max_digits=18, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='order',
            name='paid',
            field=models.DecimalField(default=Decimal('0.00'), help_text='This much has been paid already.', verbose_name='paid', max_digits=18, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='order',
            name='shipping_cost',
            field=models.DecimalField(null=True, verbose_name='shipping cost', max_digits=18, decimal_places=2, blank=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='shipping_discount',
            field=models.DecimalField(null=True, verbose_name='shipping discount', max_digits=18, decimal_places=2, blank=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='shipping_tax',
            field=models.DecimalField(default=Decimal('0.00'), verbose_name='shipping tax', max_digits=18, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='order',
            name='total',
            field=models.DecimalField(default=Decimal('0.00'), verbose_name='total', max_digits=18, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='order',
            name='user',
            field=models.ForeignKey(related_name=b'orders', on_delete=django.db.models.deletion.SET_NULL, verbose_name='user', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
    ]
