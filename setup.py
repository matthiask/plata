#!/usr/bin/env python

import os
from setuptools import setup, find_packages

import plata

setup(name='Plata',
    version=plata.__version__,
    description='Plata - the lean and mean Django-based Shop',
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.rst')).read(),
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
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
