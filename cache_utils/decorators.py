# -*- coding: utf-8 -*-

import logging
from hashlib import sha256

from cache_utils.utils import _cache_key, _func_info, _func_type, sanitize_memcached_key
from django.core.cache import caches
from django.db import models
from django.utils.encoding import smart_str

from django.utils.functional import wraps

logger = logging.getLogger("cache_utils")


class CacheRegistry(object):
    def register_key(self, model_list, key):
        cache_backend = caches['default']

        for model in model_list:
            model_key = model._meta.label_lower
            registered_keys = cache_backend.get(model_key)
            if not registered_keys:
                cache_backend.set(model_key, [key])
            else:
                if key not in registered_keys:
                    registered_keys.append(key)
                cache_backend.set(model_key, registered_keys)

    def retrieve_keys(self, model):
        cache_backend = caches['default']
        return cache_backend.get(model._meta.label_lower)


registry = CacheRegistry()


def cached(timeout, group=None, backend='default', key=None, model_list=[], hashed=False, object_attrs=None):
    """ Caching decorator. Can be applied to function, method or classmethod.
    Supports bulk cache invalidation and invalidation for exact parameter
    set. Cache keys are human-readable because they are constructed from
    callable's full name and arguments and then sanitized to make
    memcached happy.

    It can be used with or without group_backend. Without group_backend
    bulk invalidation is not supported.

    Wrapped callable gets `invalidate` methods. Call `invalidate` with
    same arguments as function and the result for these arguments will be
    invalidated.
    """
    if key:
        def test(*args, **kwargs):
            args = list(args)
            args[0] = key
            return sanitize_memcached_key(_cache_key(*args, **kwargs))
        _get_key = test
    else:
        if hashed:
            def _get_hashed_key(*args, **kwargs):
                key = _cache_key(*args, **kwargs)
                return sha256(smart_str(key).encode()).hexdigest()
            _get_key = _get_hashed_key
        else:
            _get_key = lambda *args, **kwargs: sanitize_memcached_key(_cache_key(*args, **kwargs))

    if group:
        backend_kwargs = {'group': group}
    else:
        backend_kwargs = {}

    cache_backend = caches[backend]

    def _cached(func):
        func_type = _func_type(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            full_name(*args)

            # try to get the value from cache
            key = _get_key(wrapper._full_name, func_type, args, kwargs, object_attrs)
            value = cache_backend.get(key, **backend_kwargs)

            # in case of cache miss recalculate the value and put it to the cache
            if value is None:
                logger.debug("Cache MISS: %s" % key)
                value = func(*args, **kwargs)
                cache_backend.set(key, value, timeout, **backend_kwargs)
                logger.debug("Cache SET: %s" % key)
            else:
                logger.debug("Cache HIT: %s" % key)
            registry.register_key(model_list, key)
            return value

        def invalidate(*args, **kwargs):
            """
            Invalidates cache result for function called with passed arguments
            """
            if not hasattr(wrapper, '_full_name'):
                return

            key = _get_key(wrapper._full_name, 'function', args, kwargs)
            cache_backend.delete(key, **backend_kwargs)
            logger.debug("Cache DELETE: %s" % key)

        def force_recalc(*args, **kwargs):
            """
            Forces a call to the function & sets the new value in the cache
            """
            full_name(*args)

            key = _get_key(wrapper._full_name, func_type, args, kwargs)
            value = func(*args, **kwargs)
            cache_backend.set(key, value, timeout, **backend_kwargs)
            return value

        def full_name(*args):
            # full name is stored as attribute on first call
            if not hasattr(wrapper, '_full_name'):
                name, _args = _func_info(func, args)
                wrapper._full_name = name

        def require_cache(*args, **kwargs):
            """
            Only pull from cache, do not attempt to calculate
            """
            full_name(*args)
            key = _get_key(wrapper._full_name, func_type, args, kwargs)
            logger.debug("Require cache %s" % key)
            value = cache_backend.get(key, **backend_kwargs)
            if not value:
                logger.info("Could not find required cache %s" % key)
                raise NoCachedValueException
            return value

        def get_cache_key(*args, **kwargs):
            """ Returns name of cache key utilized """
            full_name(*args)
            key = _get_key(wrapper._full_name, 'function', args, kwargs)
            return key

        wrapper.require_cache = require_cache
        wrapper.invalidate = invalidate
        wrapper.force_recalc = force_recalc
        wrapper.get_cache_key = get_cache_key
        return wrapper
    return _cached


class NoCachedValueException(Exception):
    pass

def invalidate_model(sender, instance, *args, **kwargs):
    cache_backend = caches['default']
    keys = registry.retrieve_keys(sender)
    if keys:
        for key in keys:
            cache_backend.delete(key)

models.signals.post_save.connect(invalidate_model)
