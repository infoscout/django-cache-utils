# -*- coding: utf-8 -*-

import logging
from typing import List, Type

from django.core.cache import caches
from django.db import models
from django.db.models import Model
from django.utils.functional import wraps

from cache_utils.utils import _cache_key, _func_info, _func_type, sanitize_memcached_key

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


def cached(timeout: int, group: str = None, backend='default', key: str = None, model_list: List[Type[Model]] = None):
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
    if model_list is None:
        model_list = []

    def _get_key_provided(*args, **kwargs):
        args = list(args)
        args[0] = key
        return sanitize_memcached_key(_cache_key(*args, **kwargs))

    def _get_key_unprovided(*args, **kwargs):
        return sanitize_memcached_key(_cache_key(*args, **kwargs))

    if key:
        _get_key = _get_key_provided
    else:
        _get_key = _get_key_unprovided

    if group:
        backend_kwargs = {'group': group}
    else:
        backend_kwargs = {}

    cache_backend = caches[backend]

    def _cached(func):
        func_type = _func_type(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            full_name, _ = _func_info(func, args)

            # try to get the value from cache
            _key = _get_key(full_name, func_type, args, kwargs)
            value = cache_backend.get(_key, **backend_kwargs)

            # in case of cache miss recalculate the value and put it to the cache
            if value is None:
                logger.debug(f"Cache MISS: {_key}")
                value = func(*args, **kwargs)
                cache_backend.set(_key, value, timeout, **backend_kwargs)
                logger.debug(f"Cache SET: {_key}")
            else:
                logger.debug(f"Cache HIT: {_key}")
            registry.register_key(model_list, _key)
            return value

        def invalidate(*args, **kwargs):
            """
            Invalidates cache result for function called with passed arguments
            """
            full_name, _ = _func_info(func, args)
            _key = _get_key(full_name, 'function', args, kwargs)
            _del = cache_backend.delete(_key, **backend_kwargs)
            if _del:
                logger.debug(f"Cache DELETE: {_key}")

        def force_recalc(*args, **kwargs):
            """
            Forces a call to the function & sets the new value in the cache
            """
            full_name, _ = _func_info(func, args)
            _key = _get_key(full_name, func_type, args, kwargs)
            value = func(*args, **kwargs)
            cache_backend.set(_key, value, timeout, **backend_kwargs)
            return value

        def require_cache(*args, **kwargs):
            """
            Only pull from cache, do not attempt to calculate
            """
            full_name, _ = _func_info(func, args)
            _key = _get_key(full_name, func_type, args, kwargs)
            logger.debug(f"Require cache {_key}")
            value = cache_backend.get(_key, **backend_kwargs)
            if not value:
                logger.info(f"Could not find required cache {_key}")
                raise NoCachedValueException
            return value

        def get_cache_key(*args, **kwargs):
            """ Returns name of cache key utilized """
            full_name, _ = _func_info(func, args)
            return _get_key(full_name, 'function', args, kwargs)

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
