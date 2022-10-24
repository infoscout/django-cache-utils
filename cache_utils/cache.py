import logging
import sys

from django.core.cache import caches


logger = logging.getLogger("cache_utils")


def _generate_key(key):
    """ Serializes a tuple into a key for caching
    """
    if isinstance(key, (list, tuple)):
        return "-".join(key)
    return key


def get(key, backend='default'):
    """ Wrapper to get from cache.
    """
    cache = caches[backend]
    key = _generate_key(key)
    val = cache.get(key)

    if val:
        logger.debug("Cache HIT: %s" % key)
    else:
        logger.debug("Cache MISS: %s" % key)

    return val


def set(key, value, backend='default'):
    """ Wrapper to set key/value cache
    """
    cache = caches[backend]
    key = _generate_key(key)

    val = cache.set(key, value)
    logger.debug("Cache SET: %s - Size: %s" % (key, sys.getsizeof(value)))

    return val


def delete(key, backend='default'):
    """ Wrapper to delete key/value cache
    """
    cache = caches[backend]
    key = _generate_key(key)

    val = cache.delete(key)
    logger.debug("Cache DELETE: %s" % key)
    return val
