from __future__ import absolute_import, unicode_literals

from django.db.models import Model


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
