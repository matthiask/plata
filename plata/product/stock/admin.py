from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

import plata
from plata.product.stock import models


if plata.settings.PLATA_STOCK_TRACKING:
    TYPE_CHOICES = [("", "---------")]
    TYPE_CHOICES.append((_("initial stock"), models.StockTransaction.TYPE_CHOICES[:2]))
    TYPE_CHOICES.append(
        (_("purchases and sales"), models.StockTransaction.TYPE_CHOICES[2:4])
    )
    TYPE_CHOICES.append(
        (_("stock management"), models.StockTransaction.TYPE_CHOICES[4:6])
    )
    TYPE_CHOICES.append(
        (_("generic warehousing"), models.StockTransaction.TYPE_CHOICES[6:8])
    )
    TYPE_CHOICES.append((_("internal use"), models.StockTransaction.TYPE_CHOICES[8:]))

    class StockTransactionForm(forms.ModelForm):
        type = forms.ChoiceField(choices=TYPE_CHOICES)

    admin.site.register(models.Period, list_display=("name", "notes", "start"))

    admin.site.register(
        models.StockTransaction,
        date_hierarchy="created",
        form=StockTransactionForm,
        list_display=(
            "period",
            "created",
            "product",
            "type",
            "change",
            "order",
            "notes",
        ),
        list_display_links=("created",),
        list_filter=("period", "type"),
        raw_id_fields=("product", "order", "payment"),
        search_fields=("change", "notes", "name", "sku"),
    )
