#!/usr/bin/env python
from setuptools import setup


version = '2.0.0'


setup(
    name='django-cache-utils',
    version=version,
    author='Mikhail Korobov',
    author_email='kmike84@gmail.com',
    packages=['cache_utils'],
    url='http://bitbucket.org/kmike/django-cache-utils/',
    download_url='http://bitbucket.org/kmike/django-cache-utils/get/tip.zip',
    license='MIT license',
    description=(
        "Caching decorator and django cache backend with advanced invalidation ability and dog-pile effect prevention"
    ),
    long_description=open('README.md').read(),
    requires=['Django>=1.5', 'python_memcached'],
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
