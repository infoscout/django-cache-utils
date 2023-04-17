# -*- coding: utf-8 -*-

import logging
from functools import partial
from typing import Callable, Optional, List, Type, Any

from django.core.cache import caches
from django.db import models
from django.db.models import Model
from django.utils.functional import wraps

from cache_utils.utils import get_cache_key

logger = logging.getLogger("cache_utils")


class CacheRegistry:
    def register_key(self, model_list: List[Type[Model]], key: str) -> None:
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

    def retrieve_keys(self, model: Type[Model]) -> List[str]:
        cache_backend = caches['default']
        return cache_backend.get(model._meta.label_lower) or []


registry = CacheRegistry()


def cached(
        timeout: int,
        group: Optional[str] = None,
        backend: str = 'default',
        key: Optional[str] = None,
        model_list: Optional[List[Type[Model]]] = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Caching decorator. Can be applied to function, method or classmethod.
    Supports bulk cache invalidation and invalidation for exact parameter
    set.

    If function arguments or keyword arguments are not hashable, then the
    'key' parameter must be supplied. Otherwise, a TypeError will be raised.

    It can be used with or without group_backend. Without group_backend
    bulk invalidation is not supported.

    Wrapped callable gets `invalidate` methods. Call `invalidate` with
    same arguments as function and the result for these arguments will be
    invalidated.
    """
    if model_list is None:
        model_list = []
    if group:
        backend_kwargs = {'group': group}
    else:
        backend_kwargs = {}
    cache_backend = caches[backend]

    def _cached(func: Callable[..., Any]) -> Callable[..., Any]:
        orig_key = key

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # try to get the value from cache
            _key = get_key(orig_key, func, args, kwargs)
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

        def invalidate(*args, **kwargs) -> bool:
            """
            Invalidates cache result for function called with passed arguments
            """
            _key = get_key(orig_key, func, args, kwargs)
            logger.debug(f"Cache DELETE: {_key}")
            return bool(cache_backend.delete(_key, **backend_kwargs))

        def force_recalc(*args, **kwargs) -> Any:
            """
            Forces a call to the function & sets the new value in the cache
            """
            _key = get_key(orig_key, func, args, kwargs)
            value = func(*args, **kwargs)
            cache_backend.set(_key, value, timeout, **backend_kwargs)
            return value

        def require_cache(*args, **kwargs) -> Any:
            """
            Only pull from cache, do not attempt to calculate
            """
            _key = get_key(orig_key, func, args, kwargs)
            logger.debug(f"Require cache {_key}")
            value = cache_backend.get(_key, default=None, **backend_kwargs)
            if value is None:
                logger.info(f"Could not find required cache {_key}")
                raise NoCachedValueException
            return value

        def get_key(orig_key: Optional[str], func: Callable[..., Any], *args, **kwargs):
            if orig_key is None:
                return get_cache_key(func, args, kwargs)
            else:
                return orig_key

        wrapper.invalidate = invalidate
        wrapper.force_recalc = force_recalc
        wrapper.require_cache = require_cache
        wrapper.get_cache_key = partial(get_key, key, func)

        return wrapper

    return _cached


class NoCachedValueException(Exception):
    pass


def invalidate_model(sender: Type[Model], instance: Model, *args, **kwargs):
    cache_backend = caches['default']
    keys = registry.retrieve_keys(sender)
    if keys:
        for key in keys:
            cache_backend.delete(key)


models.signals.post_save.connect(invalidate_model)
