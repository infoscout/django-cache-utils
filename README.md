# django-cache-utils

[![CircleCI](https://circleci.com/gh/infoscout/django-cache-utils.svg?style=svg)](https://circleci.com/gh/infoscout/django-cache-utils)
[![codecov](https://codecov.io/gh/infoscout/django-cache-utils/branch/master/graph/badge.svg)](https://codecov.io/gh/infoscout/django-cache-utils)

django-cache-utils provides utils for make cache-related work easier:

* `cached` decorator. It can be applied to function, method or classmethod
  and can be used with any django cache backend (built-in or third-party like
  django-newcache).

  Supports fine-grained invalidation for exact parameter set (with any backend)
  and bulk cache invalidation (only with ``group_backend``). Cache keys are
  human-readable because they are constructed from callable's full name and
  arguments and then sanitized to make memcached happy.

  Wrapped callable gets ``invalidate`` methods. Call ``invalidate`` with
  same arguments as function and the cached result for these arguments will be
  invalidated.

* `group_backend`. It is a django memcached cache backend with group O(1)
  invalidation ability, dog-pile effect prevention using MintCache algorythm
  and project version support to allow gracefull updates and multiple django
  projects on same memcached instance.
  Long keys (>250) are auto-truncated and appended with md5 hash.


* `cache_utils.cache get`, `cache_utils.cache.set`, `cache_utils.delete` are wrappers
  for the standard django cache get, set, delete calls. Implements additional logging
  and support for non-string keys.


### Installation

```shell
$ pip install djcacheutils
```

and then (optional):

```python
# settings.py
INSTALLED_APPS = (
    'cache_utils',
    ...
)
CACHES = {
    'default': {
        'BACKEND': 'cache_utils.group_backend.CacheClass',
        'LOCATION': '127.0.0.1:11211',
    },
}
```

### Usage

`cached` decorator can be used with any django caching backend (built-in or third-party like django-newcache)::

```python
from cache_utils.decorators import cached

@cached(60)
def foo(x, y=0):
    print 'foo is called'
    return x+y

foo(1, 2) # foo is called
foo(1, 2)

foo(5, 6) # foo is called
foo(5, 6)

# Invalidation
foo.invalidate(1, 2)
foo(1, 2) # foo is called

# Force calculation
foo(5, 6)
foo.force_recalc(5, 6) # foo is called

foo(x=2) # foo is called
foo(x=2)

# Require cache
foo.require_cache(7, 8) # NoCachedValueException is thrown
```

The `@cached` decorator is also supported on class methods

```python
class Foo(object):
    @cached(60)
    def foo(self, x, y):
        print "foo is called"
        return x + y

obj = Foo()
obj.foo(1, 2) # foo is called
obj.foo(1, 2)
```

With ``group_backend`` `cached` decorator supports bulk O(1) invalidation::

```python
from django.db import models
from cache_utils.decorators import cached

class CityManager(models.Manager):

    # cache a method result. 'self' parameter is ignored
    @cached(60*60*24, 'cities')
    def default(self):
        return self.active()[0]

    # cache a method result. 'self' parameter is ignored, args and
    # kwargs are used to construct cache key
    @cached(60*60*24, 'cities')
    def get(self, *args, **kwargs):
        return super(CityManager, self).get(*args, **kwargs)


class City(models.Model):
    # ... field declarations

    objects = CityManager()

    # an example how to cache django model methods by instance id
    def has_offers(self):
        @cached(30)
        def offer_count(pk):
            return self.offer_set.count()
        return offer_count(self.pk) > 0

# cache the function result based on passed parameter
@cached(60*60*24, 'cities')
def get_cities(slug)
    return City.objects.get(slug=slug)


# cache for 'cities' group can be invalidated at once
def invalidate_city(sender, **kwargs):
    cache.invalidate_group('cities')
pre_delete.connect(invalidate_city, City)
post_save.connect(invalidate_city, City)
```

You can force cache to be recalculated:

```python
@cached
def calc_function(x, y):
    return x*y

x = calc_function.force_recalc(x, y)
```

### Cache Keys


By default, django-cache-utils constructs a key based on the function name, line number, args, and kwargs. Example:

```python
@cached(60)
def foo(a1):
   ...

print foo.get_cache_key('test') # ==> '[cached]package.module:15(('test',))'
```

Note given the line-number is included in the cache key, simple tweaks to a module not releveant to the @cached function will create a new cache key (and thus upon release old cached items will not get hit).

In these instances, it's recommended to provide an explicit `key` kwarg argument to the `@cached` decorator.

```python
@cached(60, key='foo')
def foo(a1):
   ...

print foo.get_cache_key('test') # ==> '[cached]foo(('test',))'
```

### Notes

If decorated function returns None cache will be bypassed.

django-cache-utils use 2 reads from memcached to get a value if 'group'
argument is passed to 'cached' decorator::

```python
@cached(60)
def foo(param)
    return ..

@cached(60, 'my_group')
def bar(param)
    return ..

# 1 read from memcached
value1 = foo(1)

# 2 reads from memcached + ability to invalidate all values at once
value2 = bar(1)
```

### Logging

Turn on `cache_utils` logger to DEBUG to log all cache set, hit, deletes.

### Running tests

```shell
$ python setup.py test
```
