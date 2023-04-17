# -*- coding: utf-8 -*-

from unittest import TestCase

from django.core.cache import cache

from cache_utils.decorators import cached


def foo(a, b):
    pass


class Foo(object):

    def foo(self, a, b):
        pass

    @classmethod
    def bar(cls, x):
        pass


class Store(object):
    """ Class for encoding error test """

    def __unicode__(self):
        return u'Вася'

    def __repr__(self):
        return u'Вася'.encode('utf8')


class ClearMemcachedTest(TestCase):

    def tearDown(self):
        pass
        # cache._cache.flush_all()

    def setUp(self):
        pass
        # cache._cache.flush_all()


class InvalidationTest(ClearMemcachedTest):

    def test_group_invalidation(self):
        cache.set('vasia', 'foo', 60, group='names')
        cache.set('petya', 'bar', 60, group='names')
        cache.set('red', 'good', 60, group='colors')

        self.assertEqual(cache.get('vasia', group='names'), 'foo')
        self.assertEqual(cache.get('petya', group='names'), 'bar')
        self.assertEqual(cache.get('red', group='colors'), 'good')

        cache.invalidate_group('names')
        self.assertEqual(cache.get('petya', group='names'), None)
        self.assertEqual(cache.get('vasia', group='names'), None)
        self.assertEqual(cache.get('red', group='colors'), 'good')

        cache.set('vasia', 'foo', 60, group='names')
        self.assertEqual(cache.get('vasia', group='names'), 'foo')

    def test_func_invalidation(self):
        self.call_count = 0

        @cached(60)
        def my_func(a, b):
            self.call_count += 1
            return self.call_count

        self.assertEqual(my_func(1, 2), 1)
        self.assertEqual(my_func(1, 2), 1)
        self.assertEqual(my_func(3, 2), 2)
        self.assertEqual(my_func(3, 2), 2)
        my_func.invalidate(3, 2)
        self.assertEqual(my_func(1, 2), 1)
        self.assertEqual(my_func(3, 2), 3)
        self.assertEqual(my_func(3, 2), 3)

    def test_method_invalidation(self):
        self.call_count = 0
        this = self

        class Foo(object):
            @cached(60)
            def bar(self, x):
                this.call_count += 1
                return this.call_count

        foo = Foo()
        self.assertEqual(foo.bar(1), 1)
        self.assertEqual(foo.bar(1), 1)
        Foo.bar.invalidate(1)
        self.assertEqual(foo.bar(1), 2)

    def test_invalidate_nonexisting(self):
        @cached(60)
        def foo(x):
            return 1
        foo.invalidate(5)  # this shouldn't raise exception


class DecoratorTest(ClearMemcachedTest):

    def test_decorator(self):
        self._x = 0

        @cached(60, group='test-group')
        def my_func(params=""):
            self._x = self._x + 1
            return u"%d%s" % (self._x, params)

        self.assertEqual(my_func(), "1")
        self.assertEqual(my_func(), "1")

        self.assertEqual(my_func("x"), u"2x")
        self.assertEqual(my_func("x"), u"2x")

        self.assertEqual(my_func(u"Василий"), u"3Василий")
        self.assertEqual(my_func(u"Василий"), u"3Василий")

        self.assertEqual(my_func(u"й"*240), u"4"+u"й"*240)
        self.assertEqual(my_func(u"й"*240), u"4"+u"й"*240)

        self.assertEqual(my_func(u"Ы"*500), u"5"+u"Ы"*500)
        self.assertEqual(my_func(u"Ы"*500), u"5"+u"Ы"*500)

    def test_key_override(self):
        """
        Test the cache key naming.
        """

        @cached(60*5, key='foo')
        def foo():
            return 'test'

        key = foo.get_cache_key()
        self.assertEqual(key, 'foo')

        # Now test with args and kwargs argo
        @cached(60*5)
        def bar(i, foo='bar'):
            return i * 5

        key = bar.get_cache_key(2, foo='hello')
        self.assertEqual(key, "[cached]bar((2,){'foo':'hello'})")
