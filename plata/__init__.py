VERSION = (0, 0, 1)
__version__ = '.'.join(map(str, VERSION))


import logging
logger = logging.getLogger('plata')


# Do not use Django settings at module level as recommended
from django.utils.functional import LazyObject

class LazySettings(LazyObject):
    def _setup(self):
        from plata import default_settings
        self._wrapped = Settings(default_settings)

class Settings(object):
    def __init__(self, settings_module):
        for setting in dir(settings_module):
            if setting == setting.upper():
                setattr(self, setting, getattr(settings_module, setting))

settings = LazySettings()


_shop_instance = None
def register(instance):
    logger.debug('Registering shop instance: %s' % instance)

    global _shop_instance
    _shop_instance = instance

def shop_instance():
    # Load default URL patterns to ensure that the shop
    # object has been created
    from django.core.urlresolvers import get_resolver
    get_resolver(None)._populate()

    return _shop_instance
