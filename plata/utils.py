from decimal import Decimal
import simplejson

from django.core.serializers.json import DjangoJSONEncoder


try:
    simplejson.dumps([42], use_decimal=True)
except TypeError:
    raise Exception('simplejson>=2.1 with support for use_decimal required.')


class JSONFieldDescriptor(object):
    def __init__(self, field):
        self.field = field

    def __get__(self, obj, objtype):
        cache_field = '_cached_jsonfield_%s' % self.field
        if not hasattr(obj, cache_field):
            try:
                setattr(obj, cache_field, simplejson.loads(getattr(obj, self.field),
                    use_decimal=True))
            except (TypeError, ValueError):
                setattr(obj, cache_field, {})
        return getattr(obj, cache_field)

    def __set__(self, obj, value):
        setattr(obj, '_cached_jsonfield_%s' % self.field, value)
        setattr(obj, self.field, simplejson.dumps(value, use_decimal=True,
            cls=DjangoJSONEncoder))
