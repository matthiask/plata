from __future__ import absolute_import, unicode_literals

import datetime
import logging
import re
import simplejson as json

from django import forms
from django.db import models
from django.utils.dateparse import parse_date, parse_datetime, parse_time
from django.utils import six
from django.utils.functional import curry
from django.utils.translation import ugettext_lazy as _

import plata


try:
    json.dumps([42], use_decimal=True)
except TypeError:  # pragma: no cover
    raise Exception('simplejson>=2.1 with support for use_decimal required.')


#: Field offering all defined currencies
CurrencyField = curry(
    models.CharField,
    _('currency'),
    max_length=3,
    choices=list(zip(plata.settings.CURRENCIES, plata.settings.CURRENCIES)),
)


def json_encode_default(o):
    # See "Date Time String Format" in the ECMA-262 specification.
    if isinstance(o, datetime.datetime):
        return o.strftime('%Y-%m-%dT%H:%M:%S.%f%z')
    elif isinstance(o, datetime.date):
        return o.strftime('%Y-%m-%d')
    elif isinstance(o, datetime.time):
        return o.strftime('%H:%M:%S.%f%z')
    raise TypeError('Cannot encode %r' % o)


_PATTERNS = [
    (re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'), (
        lambda value: datetime.datetime.strptime(
            value,
            '%Y-%m-%dT%H:%M:%S.%f'),
        lambda value: datetime.datetime.strptime(
            value,
            '%Y-%m-%dT%H:%M:%S'),
        lambda value: parse_datetime(value),
    )),
    (re.compile(r'\d{4}-\d{2}-\d{2}'), (
        lambda value: parse_date(value),
    )),
    (re.compile(r'\d{2}:\d{2}:\d{2}'), (
        lambda value: parse_time(value),
    )),
]


def json_decode_hook(data):
    for key, value in list(data.items()):
        if not isinstance(value, six.string_types):
            continue

        for regex, fns in _PATTERNS:
            if regex.match(value):
                for fn in fns:
                    try:
                        data[key] = fn(value)
                        break
                    except ValueError:
                        pass

                break

    return data


class JSONFormField(forms.fields.CharField):
    def clean(self, value, *args, **kwargs):
        if value:
            try:
                # Run the value through JSON so we can normalize formatting
                # and at least learn about malformed data:
                value = json.dumps(
                    json.loads(
                        value,
                        use_decimal=True,
                        object_hook=json_decode_hook,
                    ),
                    use_decimal=True,
                    default=json_encode_default,
                )
            except ValueError:
                raise forms.ValidationError("Invalid JSON data!")

        return super(JSONFormField, self).clean(value, *args, **kwargs)


class JSONField(six.with_metaclass(models.SubfieldBase, models.TextField)):
    """
    TextField which transparently serializes/unserializes JSON objects

    See:
    http://www.djangosnippets.org/snippets/1478/
    """

    formfield = JSONFormField

    def to_python(self, value):
        """Convert our string value to JSON after we load it from the DB"""

        if isinstance(value, dict):
            return value
        elif isinstance(value, six.string_types):
            # Avoid asking the JSON decoder to handle empty values:
            if not value:
                return {}

            try:
                return json.loads(
                    value, use_decimal=True,
                    object_hook=json_decode_hook)
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
        """
        Extract our value from the passed object and return it in string form
        """

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
            value = json.dumps(
                value, use_decimal=True,
                default=json_encode_default)

        assert isinstance(value, six.string_types)

        return value

    def value_from_object(self, obj):
        return json.dumps(
            super(JSONField, self).value_from_object(obj),
            default=json_encode_default, use_decimal=True)


try:  # pragma: no cover
    from south.modelsinspector import add_introspection_rules
    JSONField_introspection_rule = ((JSONField,), [], {},)
    add_introspection_rules(
        rules=[JSONField_introspection_rule],
        patterns=["^plata\.fields"])
except ImportError:
    pass
