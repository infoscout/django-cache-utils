# -*- coding: utf-8 -*-

from unittest import TestCase

from django.core.cache import cache

from cache_utils.decorators import cached
from cache_utils.utils import sanitize_memcached_key, _func_type, _func_info


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


class FuncTypeTest(TestCase):

    def assertFuncType(self, func, tp):
        self.assertEqual(_func_type(func), tp)

    def test_func(self):
        self.assertFuncType(foo, 'function')

    def test_method(self):
        self.assertFuncType(Foo.foo, 'method')

    def test_classmethod(self):
        self.assertFuncType(Foo.bar, 'classmethod')


class FuncInfoTest(TestCase):

    def assertFuncInfo(self, func, args_in, name, args_out):
        info = _func_info(func, args_in)
        self.assertEqual(info[0], name)
        self.assertEqual(info[1], args_out)

    def test_func(self):
        self.assertFuncInfo(foo, [1, 2], 'cache_utils.tests.foo:11', [1, 2])

    def test_method(self):
        foo_obj = Foo()
        self.assertFuncInfo(Foo.foo, [foo_obj, 1, 2], 'cache_utils.tests.Foo.foo:17', [1, 2])

    def test_classmethod(self):
        self.assertFuncInfo(Foo.bar, [Foo, 1], 'cache_utils.tests.Foo.bar:20', [1])


class SanitizeTest(TestCase):

    def test_sanitize_keys(self):
        key = u"12345678901234567890123456789012345678901234567890"
        self.assertTrue(len(key) >= 40)
        key = sanitize_memcached_key(key, 40)
        self.assertTrue(len(key) <= 40)


class ClearMemcachedTest(TestCase):

    def tearDown(self):
        cache._cache.flush_all()

    def setUp(self):
        cache._cache.flush_all()


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
        self.assertEqual(key, '[cached]foo()')

        # Now test with args and kwargs argo
        @cached(60*5, key='func_with_args')
        def bar(i, foo='bar'):
            return i * 5

        key = bar.get_cache_key(2, foo='hello')
        self.assertEqual(key, "[cached]func_with_args((2,){'foo':'hello'})")
