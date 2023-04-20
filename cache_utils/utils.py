from collections import OrderedDict
from hashlib import md5
from typing import Tuple

from django.utils.encoding import smart_str
import six


CONTROL_CHARACTERS = set([chr(i) for i in range(0, 33)])
CONTROL_CHARACTERS.add(chr(127))


def sanitize_memcached_key(key, max_length=250):
    """ Removes control characters and ensures that key will
        not hit the memcached key length limit by replacing
        the key tail with md5 hash if key is too long.
    """
    key = ''.join([c for c in key if c not in CONTROL_CHARACTERS])
    if len(key) > max_length:
        try:
            from django.utils.encoding import force_bytes
            return md5(force_bytes(key)).hexdigest()
        except ImportError:  # Python 2
            hash = md5(key).hexdigest()
        key = key[:max_length - 33] + '-' + hash
    return key


def _args_to_unicode(args, kwargs):
    key = ""
    if args:
        key += smart_str(args)
    if kwargs:
        key += smart_str(kwargs)
    return key


def _func_type(func):
    """ returns if callable is a function, method or a classmethod """
    argnames = six.get_function_code(func).co_varnames[:six.get_function_code(func).co_argcount]
    if len(argnames) > 0:
        if argnames[0] == 'self':
            return 'method'
        if argnames[0] == 'cls':
            return 'classmethod'
    return 'function'


def _func_info(func, args):
    ''' introspect function's or method's full name.
    Returns a tuple (name, normalized_args,) with
    'cls' and 'self' removed from normalized_args '''

    func_type = _func_type(func)
    lineno = ":%s" % six.get_function_code(func).co_firstlineno

    if func_type == 'function':
        name = ".".join([func.__module__, func.__name__]) + lineno
        return name, args

    class_name = args[0].__class__.__name__
    if func_type == 'classmethod':
        class_name = args[0].__name__

    name = ".".join([func.__module__, class_name, func.__name__]) + lineno
    return name, args[1:]


def stringify_args(args, kwargs, object_attrs: None) -> Tuple[tuple, dict]:
    if object_attrs is None:
        object_attrs = {}

    def stringify(obj):
        if isinstance(obj, (list, tuple)):
            return obj.__class__.__name__ + "(" + ", ".join(stringify(e) for e in obj) + ")"
        elif isinstance(obj, dict):
            sorted_items = sorted(obj.items())  # sort to ensure consistent ordering for < py 3.6
            return "{" + ", ".join("{!r}: {}".format(k, stringify(v)) for k, v in sorted_items) + "}"
        elif hasattr(obj, '__dict__'):
            obj_str = obj.__class__.__name__
            attrs = {attr: str(getattr(obj, attr, None)) for attr in object_attrs.get(obj.__class__, [])}
            sorted_attrs = OrderedDict(sorted(attrs.items()))  # sort to ensure consistent ordering for < py 3.6
            return obj_str + "{" + ", ".join("{!r}: {!r}".format(k, v) for k, v in sorted_attrs.items()) + "}"
        else:
            return str(obj)


    stringified_args = tuple([stringify(a) for a in args])
    stringified_kwargs = {k: stringify(v) for k, v in kwargs.items()}
    return stringified_args, stringified_kwargs



def _cache_key(func_name, func_type, args, kwargs, object_attrs=None):
    """ Construct readable cache key """
    stringified_args, stringified_kwargs = stringify_args(args, kwargs, object_attrs)
    if func_type == 'function':
        args_string = _args_to_unicode(stringified_args, stringified_kwargs)
    else:
        args_string = _args_to_unicode(stringified_args[1:], stringified_kwargs)

    return '[cached]%s(%s)' % (func_name, args_string,)
