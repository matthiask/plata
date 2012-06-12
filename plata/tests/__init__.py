from __future__ import absolute_import

import os

if os.environ.get('PLATA_RUN_TESTS'):
    from .admin import AdminTest
    from .models import ModelTest
    from .views import ViewTest
