import os
import sys
import types

from plata.product.simple import models as product_models

# Create mock models module
models = types.ModuleType('plata.product.models')
sys.modules['plata.product.models'] = models

# Django needs a __file__ attribute in several places
models.__file__ = os.path.join(os.path.dirname(__file__), 'models.py')

# Assign attributes so they can be imported from a central place
for cls in getattr(product_models, '__all__', ('Product', 'ProductPrice', 'ProductImage', 'Category', 'Discount', 'TaxClass')):
    setattr(models, cls, getattr(product_models, cls))
