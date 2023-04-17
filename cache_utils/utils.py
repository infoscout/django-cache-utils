import hashlib
import inspect
import pickle
import re
from typing import Hashable, Callable

from django.utils.encoding import smart_str, force_bytes


def sanitize_memcached_key(cache_key: str) -> str:
    # Sanitize cache key if it's not valid
    if not re.match(r'^[a-zA-Z0-9_]{1,250}$', cache_key):
        # Replace any non-alphanumeric or underscore characters with underscores
        # cache_key = re.sub(r'[^a-zA-Z0-9_]+', '_', cache_key)
        # Trim to maximum length of 250 characters
        cache_key = cache_key[:250]
    return force_bytes(cache_key)


def get_cache_key(func: Callable, *args: Hashable, **kwargs: Hashable) -> str:
    # Get function name
    func_name = func.__name__
    # Get function type
    func_type = type(func)
    # Get function arguments
    argspec = inspect.getfullargspec(func)
    func_args = argspec.args
    # Combine function args and kwargs into a single dictionary
    func_params = {**dict(zip(func_args, args)), **kwargs}
    # Serialize function parameters
    serialized_params = []
    for key, value in sorted(func_params.items(), reverse=True):
        serialized_params.append(pickle.dumps((key, value)))
    # Combine serialized parameters into a single unique key
    unique_key = ":".join([smart_str(p) for p in serialized_params])
    # Combine function name, type, and unique key into final cache key
    cache_key = f"[cached]{func_type}:{func_name}({unique_key})"
    return sanitize_memcached_key(cache_key)
