#!/usr/bin/env python
from distutils.core import setup

version='0.7.2'

setup(
    name='django-cache-utils',
    version=version,
    author='Mikhail Korobov',
    author_email='kmike84@gmail.com',

    packages=['cache_utils'],

    url='http://bitbucket.org/kmike/django-cache-utils/',
    download_url = 'http://bitbucket.org/kmike/django-cache-utils/get/tip.zip',
    license = 'MIT license',
    description = """ Caching decorator and django cache backend with advanced invalidation ability and dog-pile effect prevention """,

    long_description = open('README.rst').read(),
    requires = ['django', 'memcached'],

    classifiers=(
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ),
)
