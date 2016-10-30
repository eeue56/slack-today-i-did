"""
Support dumping and loading of typing types.
"""
import typing
import functools

from json_tricks import nonp


def encode_type(obj):
    if isinstance(obj, type) or isinstance(obj.__class__, typing.TypingMeta):
        return {'__type_repr__': repr(obj)}
    return obj


class TypeHook(object):
    def __init__(self, types):
        self.type_lookup_map = {repr(type_obj): type_obj for type_obj in types }

    def __call__(self, dct):
        if isinstance(dct, dict) and '__type_repr__' in dct:
            return self.type_lookup_map.get(dct['__type_repr__'], dct)
        return dct


def _append_to_key(kwargs, key, obj):
    objs = []
    if key in kwargs:
        objs = list(kwargs[key])
    objs.append(obj)
    kwargs[key] = objs


def _wrap_dumper(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        _append_to_key(kwargs, 'extra_obj_encoders', encode_type)
        return fn(*args, **kwargs)
    return wrapper


def _wrap_loader(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        known_types = kwargs.pop('known_types', tuple())
        _append_to_key(kwargs, 'extra_obj_pairs_hooks', TypeHook(known_types))
        return fn(*args, **kwargs)
    return wrapper


dump = _wrap_dumper(nonp.dump)
dumps = _wrap_dumper(nonp.dumps)
load = _wrap_loader(nonp.load)
loads = _wrap_loader(nonp.loads)
