from decimal import Decimal
import simplejson

from django.core.serializers.json import DjangoJSONEncoder


try:
    simplejson.dumps([42], use_decimal=True)
except TypeError:
    raise Exception('simplejson>=2.1 with support for use_decimal required.')


class CallbackOnUpdateDict(dict):
    """Dict which executes a callback on every update"""

    def __init__(self, *args, **kwargs):
        self.callback = kwargs.pop('callback')
        super(CallbackOnUpdateDict, self).__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        ret = super(CallbackOnUpdateDict, self).__setitem__(key, value)
        self.callback(self)
        return ret

    def update(self, d):
        ret = super(CallbackOnUpdateDict, self).update(d)
        self.callback(self)
        return ret


class JSONFieldDescriptor(object):
    def __init__(self, field):
        self.field = field

    def __get__(self, obj, objtype):
        cache_field = '_cached_jsonfield_%s' % self.field
        if not hasattr(obj, cache_field):
            try:
                value = simplejson.loads(getattr(obj, self.field), use_decimal=True)
            except (TypeError, ValueError):
                value = {}

            self.__set__(obj, value)

        return getattr(obj, cache_field)

    def __set__(self, obj, value):
        if not isinstance(value, CallbackOnUpdateDict):
            value = CallbackOnUpdateDict(value,
                 # Update cached and serialized value on every write to the data dict
                callback=lambda d: self.__set__(obj, d))

        setattr(obj, '_cached_jsonfield_%s' % self.field, value)
        setattr(obj, self.field, simplejson.dumps(value, use_decimal=True,
            cls=DjangoJSONEncoder))
