#!/usr/bin/env python

import os
from setuptools import setup, find_packages


def read(filename):
    return open(os.path.join(os.path.dirname(__file__), filename)).read()


setup(
    name='Plata',
    version=__import__('plata').__version__,
    description='Plata - the lean and mean Django-based Shop',
    long_description=read('README.rst'),
    author='Matthias Kestenholz et al.',
    author_email='mk@feinheit.ch',
    url='https://github.com/fiee/plata/',
    license='BSD License',
    platforms=['OS Independent'],
    packages=find_packages(
        exclude=[],
    ),
    package_data={
        '': ['*.html', '*.txt'],
        'plata': [
            'locale/*/*/*.*',
        ],
        'plata.shop': [
            'templates/*.*',
            'templates/*/*.*',
            'templates/*/*/*.*',
            'templates/*/*/*/*.*',
        ],
    },
    install_requires=[
        'Django > 1.8',
        'simplejson>=3.8',
        'openpyxl>=2.2',
        'reportlab>=3.2',
        'pdfdocument>=3.1',
        'xlsxdocument',
        'django-countries>=3.3',
        'pytz',
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        # Our dependencies do not support Python 3 either... :-(
        # 'Programming Language :: Python :: 3.4',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
    ],
    zip_safe=False,
)
