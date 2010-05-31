#!/usr/bin/env python

import os
from setuptools import setup, find_packages
from setuptools.dist import Distribution
import pkg_resources


add_django_dependency = True
# See issues #50, #57 and #58 for why this is necessary
try:
    pkg_resources.get_distribution('Django')
    add_django_dependency = False
except pkg_resources.DistributionNotFound:
    try:
        import django
        if django.VERSION[0] >= 1 and django.VERSION[1] >= 1 and django.VERSION[2] >= 1:
            add_django_dependency = False
    except ImportError:
        pass

Distribution({
    "setup_requires": add_django_dependency and  ['Django >=1.2'] or []
})

import plata

setup(name='Plata',
    version=plata.__version__,
    description='Plata - the lean and mean Django-based Shop',
    long_description=open(os.path.join(os.path.dirname(__file__), 'README')).read(),
    author='Matthias Kestenholz',
    author_email='mk@feinheit.ch',
    url='http://github.com/matthiask/plata/',
    license='BSD License',
    platforms=['OS Independent'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
    ],
    install_requires=[
        #'Django >=1.1.1' # See http://github.com/matthiask/feincms/issues/closed#issue/50
    ],
    requires=[
    ],
    packages=['plata',
        'plata.contact',
        'plata.discount',
        'plata.payment',
        'plata.payment.modules',
        'plata.product',
        'plata.product.feincms',
        'plata.product.producer',
        'plata.product.stock',
        'plata.shop',
        'plata.shop.templatetags',
    ],
    include_package_data=True,
    zip_safe=False,
)

