from threading import local

from django import forms
from django.contrib import admin
from django.db.models import Model
from django.utils import simplejson
from django.utils.translation import ugettext_lazy as _

from . import models


# Internal state tracking helper for config fields
_discount_admin_state = local()


def jsonize(v):
    """
    Convert the discount configuration into a state in which it can be
    stored inside the JSON field.

    Some information is lost here; f.e. we only store the primary key
    of model objects, so you have to remember yourself which objects
    are meant by the primary key values.
    """

    if isinstance(v, dict):
        return dict((i1, jsonize(i2)) for i1, i2 in v.items())
    if hasattr(v, '__iter__'):
        return [jsonize(i) for i in v]
    if isinstance(v, Model):
        return v.pk
    return v


class DiscountAdminForm(forms.ModelForm):
    class Meta:
        widgets = {
            'config_json': forms.Textarea(attrs={'rows': 3}),
            }

    def __init__(self, *args, **kwargs):
        super(DiscountAdminForm, self).__init__(*args, **kwargs)

        self.fields['config_options'] = forms.MultipleChoiceField(
            choices=((key, cfg.get('title', key)) for key, cfg in self._meta.model.CONFIG_OPTIONS),
            label=_('Configuration options'),
            help_text=_('Save and continue editing to configure options.'),
            )

        _discount_admin_state._plata_discount_config_fieldsets = []

        # Determine the list of selected configuration options
        # 1. POST data
        # 2. get data from the instance we are editing
        # 3. fall back to allowing all products in the discount

        try:
            selected = self.data.getlist('config_options')
        except AttributeError:
            if self.instance.pk:
                selected = self.instance.config.keys()
            else:
                selected = None

        selected = selected or ('all',)
        self.fields['config_options'].initial = selected

        for s in selected:
            cfg = dict(self._meta.model.CONFIG_OPTIONS)[s]

            # Always create a fieldset for selected configuration options,
            # even if we do not have any form fields.
            fieldset = [
                _('Discount configuration: %s') % cfg.get('title', s),
                {'fields': []},
                ]

            for k, f in cfg.get('form_fields', []):
                self.fields['%s_%s' % (s, k)] = f

                # Set initial value if we have one already in the configuration
                if k in self.instance.config.get(s, {}):
                    f.initial = self.instance.config[s].get(k)

                fieldset[1]['fields'].append('%s_%s' % (s, k))

            _discount_admin_state._plata_discount_config_fieldsets.append(fieldset)

    def clean(self):
        data = self.cleaned_data

        if 'config_json' in self.changed_data:
            return data

        selected = data.get('config_options', [])
        config_options = {}

        for s in selected:
            cfg = dict(self._meta.model.CONFIG_OPTIONS)[s]

            option_item = {}
            for k, f in cfg.get('form_fields', []):
                key = '%s_%s' % (s, k)
                if key in data:
                    option_item[k] = data.get(key)

            config_options[s] = option_item

        data['config_json'] = simplejson.dumps(jsonize(config_options))
        return data


class DiscountAdmin(admin.ModelAdmin):
    form = DiscountAdminForm
    list_display = ('name', 'type', 'code', 'value')
    list_filter = ('type',)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super(DiscountAdmin, self).get_fieldsets(request, obj)
        fieldsets[0][1]['fields'].remove('config_json')

        fieldsets.append((_('Configuration'), {
            'fields': ('config_json', 'config_options'),
            }))

        fieldsets.extend(_discount_admin_state._plata_discount_config_fieldsets)
        del _discount_admin_state._plata_discount_config_fieldsets

        return fieldsets

admin.site.register(models.Discount, DiscountAdmin)
