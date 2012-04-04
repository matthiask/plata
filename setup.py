#!/usr/bin/env python

from distutils.core import setup
import os
import setuplib

packages, package_data = setuplib.find_packages('plata')

setup(name='Plata',
    version=__import__('plata').__version__,
    description='Plata - the lean and mean Django-based Shop',
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.rst')).read(),
    author='Matthias Kestenholz',
    author_email='mk@feinheit.ch',
    url='https://github.com/matthiask/plata/',
    license='BSD License',
    platforms=['OS Independent'],
    packages=packages,
    package_data=package_data,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
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
)
