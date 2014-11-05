# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import django.db.models.deletion
from django.conf import settings

import plata.product.stock.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.PLATA_SHOP_PRODUCT),
        ('shop', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Period',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='name')),
                ('notes', models.TextField(verbose_name='notes', blank=True)),
                ('start', models.DateTimeField(default=django.utils.timezone.now, help_text='Period starts at this time. May also be a future date.', verbose_name='start')),
            ],
            options={
                'ordering': ['-start'],
                'abstract': False,
                'get_latest_by': 'start',
                'verbose_name': 'period',
                'verbose_name_plural': 'periods',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='StockTransaction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now, verbose_name='created')),
                ('type', models.PositiveIntegerField(verbose_name='type', choices=[(10, 'initial amount'), (20, 'correction'), (30, 'purchase'), (40, 'sale'), (50, 'returns'), (60, 'reservation'), (70, 'incoming'), (80, 'outgoing'), (100, 'payment process reservation')])),
                ('change', models.IntegerField(help_text='Use negative numbers for sales, lendings and other outgoings.', verbose_name='change')),
                ('notes', models.TextField(verbose_name='notes', blank=True)),
                ('name', models.CharField(max_length=100, verbose_name='name', blank=True)),
                ('sku', models.CharField(max_length=100, verbose_name='SKU', blank=True)),
                ('line_item_price', models.DecimalField(null=True, verbose_name='line item price', max_digits=18, decimal_places=10, blank=True)),
                ('line_item_discount', models.DecimalField(null=True, verbose_name='line item discount', max_digits=18, decimal_places=10, blank=True)),
                ('line_item_tax', models.DecimalField(null=True, verbose_name='line item tax', max_digits=18, decimal_places=10, blank=True)),
                ('order', models.ForeignKey(related_name=b'stock_transactions', verbose_name='order', blank=True, to='shop.Order', null=True)),
                ('payment', models.ForeignKey(related_name=b'stock_transactions', verbose_name='order payment', blank=True, to='shop.OrderPayment', null=True)),
                ('period', models.ForeignKey(related_name=b'stock_transactions', verbose_name='period', to='stock.Period', default=plata.product.stock.models.current_period, )),
                ('product', models.ForeignKey(related_name=b'stock_transactions', on_delete=django.db.models.deletion.SET_NULL, verbose_name='product', to=settings.PLATA_SHOP_PRODUCT, null=True)),
            ],
            options={
                'ordering': ['-id'],
                'abstract': False,
                'verbose_name': 'stock transaction',
                'verbose_name_plural': 'stock transactions',
            },
            bases=(models.Model,),
        ),
    ]
