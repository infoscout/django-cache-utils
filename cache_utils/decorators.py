#coding: utf-8
from django.core.cache import cache
from django.utils.functional import wraps
from cache_utils.utils import _cache_key, _func_info, _func_type, sanitize_memcached_key

def cached(timeout, group=None):
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

    if group:
        backend_kwargs = {'group': group}
        get_key = _cache_key
    else:
        backend_kwargs = {}
        def get_key(*args, **kwargs):
            return sanitize_memcached_key(_cache_key(*args, **kwargs))

    def _cached(func):

        func_type = _func_type(func)

        @wraps(func)
        def wrapper(*args, **kwargs):

            # full name is stored as attribute on first call
            if not hasattr(wrapper, '_full_name'):
                name, _args = _func_info(func, args)
                wrapper._full_name = name

            # try to get the value from cache
            key = get_key(wrapper._full_name, func_type, args, kwargs)
            value = cache.get(key, **backend_kwargs)

            # in case of cache miss recalculate the value and put it to the cache
            if value is None:
                value = func(*args, **kwargs)
                cache.set(key, value, timeout, **backend_kwargs)
            return value

        def invalidate(*args, **kwargs):
            ''' invalidates cache result for function called with passed arguments '''
            if not hasattr(wrapper, '_full_name'):
                return
            key = get_key(wrapper._full_name, 'function', args, kwargs)
            cache.delete(key, **backend_kwargs)

        wrapper.invalidate = invalidate
        return wrapper
    return _cached
