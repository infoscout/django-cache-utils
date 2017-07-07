"""
Memcached cache backend with group O(1) invalidation ability, dog-pile
effect prevention using MintCache algorythm and project version support to allow
gracefull updates and multiple django projects on same memcached instance.
Long keys (>250) are truncated and appended with md5 hash.
"""

import time
import uuid

from django.conf import settings
from django.core.cache.backends.memcached import MemcachedCache
from django.utils.encoding import smart_str

from cache_utils.utils import sanitize_memcached_key


# This prefix is appended to the group name to prevent cache key clashes.
_VERSION_PREFIX = getattr(settings, 'VERSION', "")
_KEY_PREFIX = "_group::"

# MINT_DELAY is an upper bound on how long any value should take to
# be generated (in seconds)
MINT_DELAY = 30


class CacheClass(MemcachedCache):

    def _get_real_timeout(self, timeout):
        return timeout or self.default_timeout

    def add(self, key, value, timeout=0, group=None):
        key = self._make_key(group, key)

        timeout = self._get_real_timeout(timeout)
        refresh_time = timeout + time.time()
        real_timeout = timeout + MINT_DELAY
        packed_value = (value, refresh_time, False)

        return super(CacheClass, self).add(key, packed_value, real_timeout)

    def get(self, key, version=None, default=None, group=None):
        key = self._make_key(group, key)
        packed_value = super(CacheClass, self).get(key, default)
        if packed_value is None:
            return default
        value, refresh_time, refreshed = packed_value
        if (time.time() > refresh_time) and not refreshed:
            # Store the stale value while the cache revalidates for another
            # MINT_DELAY seconds.
            self.set(key, value, timeout=MINT_DELAY, group=group, refreshed=True)
            return default
        return value

    def set(self, key, value, timeout=0, group=None, refreshed=False):
        key = self._make_key(group, key)
        timeout = self._get_real_timeout(timeout)
        refresh_time = timeout + time.time()
        real_timeout = timeout + MINT_DELAY
        packed_value = (value, refresh_time, refreshed)
        return super(CacheClass, self).set(key, packed_value, real_timeout)

    def delete(self, key, group=None):
        key = self._make_key(group, key)
        return super(CacheClass, self).delete(key)

    def invalidate_group(self, group):
        """ Invalidates all cache keys belonging to group """
        key = "%s%s%s" % (_VERSION_PREFIX, _KEY_PREFIX, group)
        super(CacheClass, self).delete(key)

    def _make_key(self, group, key, hashkey=None):
        """ Generates a new cache key which belongs to a group, has
            _VERSION_PREFIX prepended and is shorter than memcached key length
            limit.
        """
        key = _VERSION_PREFIX + key
        if group:
            if not hashkey:
                hashkey = self._get_hashkey(group)
            key = "%s:%s-%s" % (group, key, hashkey)
        return sanitize_memcached_key(key)

    def make_key(self, key, *args, **kwargs):
        """
        A hack to make backend work correctly with django 1.3.

        Key prefixes and cache versions are now supported out of box but
        this class uses its own settings and in order to provide
        backward compatibility django's new features are not used.
        """
        return smart_str(key)

    def _get_hashkey(self, group):
        """ This can be useful sometimes if you're doing a very large number
            of operations and you want to avoid all of the extra cache hits.
        """
        key = "%s%s%s" % (_VERSION_PREFIX, _KEY_PREFIX, group)
        hashkey = super(CacheClass, self).get(key)
        if hashkey is None:
            hashkey = str(uuid.uuid4())
            super(CacheClass, self).set(key, hashkey)
        return hashkey

    def clear(self):
        self._cache.flush_all()

# ======================================
# I didn't implement methods below to work with MintCache so raise
# NotImplementedError for them.

    def incr(self, key, delta=1, group=None):
        # if group:
        #     key = self._make_key(group, key)
        # return super(CacheClass, self).incr(key, delta)
        raise NotImplementedError

    def decr(self, key, delta=1, group=None):
        # if group:
        #     key = self._make_key(group, key)
        # return super(CacheClass, self).decr(key, delta)
        raise NotImplementedError

    def get_many(self, keys, group=None):
        # hashkey = self._get_hashkey(group)
        # keys = [self._make_key(group, k, hashkey) for k in keys]
        # return super(CacheClass, self).get_many(keys)
        raise NotImplementedError
