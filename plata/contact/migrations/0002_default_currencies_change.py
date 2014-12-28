# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contact', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='currency',
            field=models.CharField(help_text='Preferred currency.', max_length=3, verbose_name='currency', choices=[(b'SEK', b'SEK'), (b'EUR', b'EUR'), (b'NOK', b'NOK'), (b'DKK', b'DKK')]),
        ),
    ]
