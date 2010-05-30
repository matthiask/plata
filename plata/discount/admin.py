from django import forms
from django.contrib import admin
from django.db.models import Model
from django.utils import simplejson
from django.utils.translation import ugettext_lazy as _

from . import models


def jsonize(v):
    if isinstance(v, dict):
        return dict((i1, jsonize(i2)) for i1, i2 in v.items())
    if hasattr(v, '__iter__'):
        return [jsonize(i) for i in v]
    if isinstance(v, Model):
        return v.pk
    return v


class DiscountAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(DiscountAdminForm, self).__init__(*args, **kwargs)

        choices = ((key, cfg.get('title', key)) for key, cfg in self._meta.model.CONFIG_OPTIONS)

        self.fields['config_options'] = forms.MultipleChoiceField(
            choices=choices,
            label=_('Configuration options'),
            help_text=_('Save and continue editing to configure options.'),
            )

        self.instance.config_fieldsets = []

        if self.instance.pk:
            selected = self.instance.config.keys()
            self.fields['config_options'].initial = selected

            for s in selected:
                cfg = dict(self._meta.model.CONFIG_OPTIONS)[s]

                fieldset = [
                    _('Discount configuration: %s') % cfg.get('title', s),
                    {'fields': []},
                    ]

                for k, f in cfg.get('form_fields', []):
                    self.fields['%s_%s' % (s, k)] = f
                    if k in self.instance.config[s]:
                        f.initial = self.instance.config[s].get(k)
                    fieldset[1]['fields'].append('%s_%s' % (s, k))

                self.instance.config_fieldsets.append(fieldset)
        else:
            self.fields['config_options'].initial = ('all',)

    def clean(self):
        data = self.cleaned_data

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

        fieldsets.append((_('Raw configuration'), {
            'fields': ('config_json',),
            'classes': ('collapse',),
            }))
        fieldsets.append((_('Configuration'), {
            'fields': ('config_options',),
            }))

        if obj:
            fieldsets.extend(obj.config_fieldsets)

        return fieldsets

admin.site.register(models.Discount, DiscountAdmin)
