from django import forms
from django.contrib import admin
from django.contrib.admin.utils import flatten_fieldsets
from django.utils.translation import gettext_lazy as _

from plata.discount import models
from plata.utils import jsonize


class DiscountAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Seems to be necessary because of the custom validation
        self.fields["config"].required = False

        choices = [
            (key, cfg.get("title", key)) for key, cfg in self._meta.model.CONFIG_OPTIONS
        ]

        self.fields["config_options"] = forms.MultipleChoiceField(
            choices=choices,
            label=_("Configuration options"),
            help_text=_("Save and continue editing to configure options."),
        )

        config_fieldsets = []

        # Determine the list of selected configuration options
        # 1. POST data
        # 2. get data from the instance we are editing
        # 3. fall back to allowing all products in the discount
        if "config_options" in self.data:
            selected = self.data.getlist("config_options")
        else:
            selected = self.instance.config.keys() if self.instance.pk else None

        selected = tuple(selected) if selected else ("all",)
        self.fields["config_options"].initial = selected

        for s in selected:
            cfg = dict(self._meta.model.CONFIG_OPTIONS)[s]

            # Always create a fieldset for selected configuration options,
            # even if we do not have any form fields.
            fieldset = [
                _("Discount configuration: %s") % cfg.get("title", s),
                {"fields": []},
            ]

            for k, f in cfg.get("form_fields", []):
                self.fields[f"{s}_{k}"] = f

                # Set initial value if we have one in the configuration
                if k in self.instance.config.get(s, {}):
                    f.initial = self.instance.config[s].get(k)

                fieldset[1]["fields"].append(f"{s}_{k}")

            config_fieldsets.append(fieldset)

        self.request._plata_discount_config_fieldsets = config_fieldsets

    def clean(self):
        data = self.cleaned_data

        if "config" in self.changed_data:
            return data

        selected = data.get("config_options", [])
        config_options = {}

        for s in selected:
            cfg = dict(self._meta.model.CONFIG_OPTIONS)[s]

            option_item = {}
            for k, _f in cfg.get("form_fields", []):
                key = f"{s}_{k}"
                if key in data:
                    option_item[k] = data.get(key)

            config_options[s] = option_item

        self.instance.config = jsonize(config_options)
        data["config"] = self.instance.config
        return data


class DiscountAdmin(admin.ModelAdmin):
    form = DiscountAdminForm
    list_display = (
        "name",
        "type",
        "is_active",
        "valid_from",
        "valid_until",
        "code",
        "value",
    )
    list_filter = ("type", "is_active")
    ordering = ("-valid_from",)
    search_fields = ("name", "code", "config")

    def get_form(self, request, obj=None, **kwargs):
        fields = kwargs.get("fields", []) or []
        if "config_options" in fields:
            fields.remove("config_options")
        form_class = super().get_form(request, obj=obj, **kwargs)
        # Generate a new type to be sure that the request stays inside this
        # request/response cycle.
        return type(form_class.__name__, (form_class,), {"request": request})

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not hasattr(request, "_plata_discount_config_fieldsets"):
            return fieldsets

        fieldsets[0][1]["fields"].remove("config")

        fieldsets.append(
            (_("Raw configuration"), {"fields": ("config",), "classes": ("collapse",)})
        )
        fieldsets.append((_("Configuration"), {"fields": ("config_options",)}))

        fieldsets.extend(request._plata_discount_config_fieldsets)

        return fieldsets

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        obj = self.model.objects.filter(pk=object_id).first() if object_id else None
        fieldsets = self.get_fieldsets(request, obj)
        ModelForm = self.get_form(
            request, obj, change=bool(obj), fields=flatten_fieldsets(fieldsets)
        )
        form_kwargs = {"instance": obj} if obj else {}
        ModelForm(**form_kwargs)  # hack to set the plata extra fieldsets on the request
        return super().changeform_view(request, object_id, form_url, extra_context)


admin.site.register(models.Discount, DiscountAdmin)
