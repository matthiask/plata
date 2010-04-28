from django.utils import simplejson


class JSONFieldDescriptor(object):
    def __init__(self, field):
        self.field = field

    def __get__(self, obj, objtype):
        if not hasattr(self, '_cached'):
            try:
                self._cached = simplejson.loads(getattr(obj, self.field))
            except (TypeError, ValueError):
                self._cached = {}
        return self._cached

    def __set__(self, obj, value):
        self._cached = value
        setattr(obj, self.field, simplejson.dumps(value))
