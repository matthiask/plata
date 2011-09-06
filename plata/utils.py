from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Model


try:
    from django.utils import simplejson
    simplejson.dumps([42], use_decimal=True)
except TypeError:
    try:
        import simplejson
        simplejson.dumps([42], use_decimal=True)
    except (ImportError, TypeError):
        raise Exception('simplejson>=2.1 with support for use_decimal required.')


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


class CallbackOnUpdateDict(dict):
    """
    ``dict`` subclass which executes a callback on every update::

        def print_values(d):
            print d

        d = CallbackOnUpdateDict({'initial': 'data'},
            callback=print_values)
    """

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
    """
    Descriptor offering access to a text field containing a JSON-encoded
    string. Requires the name of the ``TextField``::

        class MyModel(models.Model):
            data = models.TextField(blank=True)
            data_json = JSONFieldDescriptor('data')
    """

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
