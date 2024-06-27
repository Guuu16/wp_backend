# -*- coding: utf-8 -*-
"""
@Time ： 1/13/23 6:26 PM
@Auth ： gujie5
"""
from django.core.cache import cache


def get_cache_or_exc_func(key, func, *args, **kwargs):
    with cache.lock(key + 'lock'):
        result = cache.get(key)
        if result:
            return result
        else:
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result


def get_cache_or_exc_func1(key, func, *args, **kwargs):
    with cache.lock(key + 'lock'):
        result = cache.get(key)
        if result:
            return result
        else:
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result