#!/usr/bin/env python

import os
from distutils.core import setup
import plata

setup(name='Plata',
    version=plata.__version__,
    description='Plata - the lean and mean Django-based Shop',
    long_description=open(os.path.join(os.path.dirname(__file__), 'README')).read(),
    author='Matthias Kestenholz',
    author_email='mk@feinheit.ch',
    url='https://github.com/matthiask/plata/',
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
    packages=[
        'plata',
        'plata.contact',
        'plata.discount',
        'plata.payment',
        'plata.payment.modules',
        'plata.product',
        'plata.product.feincms',
        'plata.product.producer',
        'plata.product.stock',
        'plata.reporting',
        'plata.shop',
        'plata.shop.templatetags',
    ],
)

