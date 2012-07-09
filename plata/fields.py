from decimal import Decimal
import json
import logging

from django import forms
from django.db import models
from django.utils.functional import curry
from django.utils.translation import ugettext_lazy as _

import plata


#: Field offering all defined currencies
CurrencyField = curry(models.CharField, _('currency'), max_length=3, choices=zip(
    plata.settings.CURRENCIES, plata.settings.CURRENCIES))


def _encode_decimal(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError('Try yourself.')


class JSONFormField(forms.fields.CharField):
    def clean(self, value, *args, **kwargs):
        if value:
            try:
                # Run the value through JSON so we can normalize formatting and at least learn about malformed data:
                value = json.dumps(
                    json.loads(value, parse_float=Decimal),
                    default=_encode_decimal)
            except ValueError:
                raise forms.ValidationError("Invalid JSON data!")

        return super(JSONFormField, self).clean(value, *args, **kwargs)


class JSONField(models.TextField):
    """
    TextField which transparently serializes/unserializes JSON objects

    See:
    http://www.djangosnippets.org/snippets/1478/
    """

    # Used so to_python() is called
    __metaclass__ = models.SubfieldBase

    formfield = JSONFormField

    def to_python(self, value):
        """Convert our string value to JSON after we load it from the DB"""

        if isinstance(value, dict):
            return value
        elif isinstance(value, basestring):
            # Avoid asking the JSON decoder to handle empty values:
            if not value:
                return {}

            try:
                return json.loads(value, parse_float=Decimal)
            except ValueError:
                logging.getLogger("plata.fields").exception(
                    "Unable to deserialize stored JSONField data: %s", value)
                return {}
        else:
            assert value is None
            return {}

    def get_prep_value(self, value):
        """Convert our JSON object to a string before we save"""
        return self._flatten_value(value)

    def value_to_string(self, obj):
        """Extract our value from the passed object and return it in string form"""

        if hasattr(obj, self.attname):
            value = getattr(obj, self.attname)
        else:
            assert isinstance(obj, dict)
            value = obj.get(self.attname, "")

        return self._flatten_value(value)

    def _flatten_value(self, value):
        """Return either a string, JSON-encoding dict()s as necessary"""
        if not value:
            return ""

        if isinstance(value, dict):
            value = json.dumps(value, default=_encode_decimal)

        assert isinstance(value, basestring)

        return value

    def value_from_object(self, obj):
        return json.dumps(
            super(JSONField, self).value_from_object(obj),
            default=_encode_decimal)


try:
    from south.modelsinspector import add_introspection_rules

    JSONField_introspection_rule = ( (JSONField,), [], {}, )

    add_introspection_rules(rules=[JSONField_introspection_rule], patterns=["^plata\.fields"])
except ImportError:
    pass
