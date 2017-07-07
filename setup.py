#!/usr/bin/env python
from setuptools import setup, Command


version = '3.0.0'


class TestCommand(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import django
        from django.conf import settings
        from django.core.management import call_command

        settings.configure(
            CACHES={
                'default': {
                    'BACKEND': 'cache_utils.group_backend.CacheClass',
                    'LOCATION': '127.0.0.1:11211',
                },
            },
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                }
            },
            INSTALLED_APPS=('cache_utils',)
        )
        django.setup()
        call_command('test')


setup(
    name='djcacheutils',
    version=version,
    author='Mikhail Korobov',
    author_email='kmike84@gmail.com',
    packages=['cache_utils'],
    url='https://github.com/infoscout/django-cache-utils',
    license='MIT license',
    description=(
        "Caching decorator and django cache backend with advanced invalidation ability and dog-pile effect prevention"
    ),
    long_description=open('README.md').read(),
    install_requires=['Django >= 1.8', 'python_memcached'],
    classifiers=(
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.8',
        'Framework :: Django :: 1.9',
        'Framework :: Django :: 1.10',
        'Framework :: Django :: 1.11',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ),
    cmdclass={'test': TestCommand},
)
