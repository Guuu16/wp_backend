# -*- coding: utf-8 -*-
"""
@Time ： 1/12/23 10:21 AM
@Auth ： gujie5
"""
from functools import wraps
import traceback
import requests
import json


def RequestGetDecorator(func):
    '''
        bug rest request get decorator
    '''

    @wraps(func)
    def wrapper(*args, **kwargs):
        req, params = func(*args, **kwargs)
        retry_count = 3
        while retry_count > 0:
            try:
                res = requests.get(req, params=params, timeout=3000,verify=False)
                break
            except requests.exceptions.ReadTimeout:
                print("retry:", retry_count)
                retry_count -= 1
            except Exception as e:
                traceback.print_exc()
        if retry_count <= 0:
            raise requests.exceptions.ReadTimeout

        # print(res.url)

        # res.status_codemust be 2XX
        if res.status_code // 200 != 1:
            return False, res.text
        result = json.loads(res.content.decode('utf-8'))
        if type(result) == dict:
            return not result.get('error'), result
        else:
            return True, result

    return wrapper


def RequestPutDecorator(func):
    '''
        bug rest request put decorator
    '''

    @wraps(func)
    def wrapper(*args, **kwargs):
        req, params = func(*args, **kwargs)
        retry_count = 3
        while retry_count > 0:
            try:
                res = requests.put(req, json=params, timeout=3000,verify=False)
                break
            except requests.exceptions.ReadTimeout:
                print("retry:", retry_count)
                retry_count -= 1
            except Exception as e:
                traceback.print_exc()

        if retry_count <= 0:
            raise requests.exceptions.ReadTimeout

        # res.status_codemust be 2XX
        if res.status_code // 200 != 1:
            return False, res.text
        result = json.loads(res.content.decode('utf-8'))
        if type(result) == dict:
            return not result.get('error'), result
        else:
            return True, result

    return wrapper


def RequestPostDecorator(func):
    '''
        bug rest request post decorator
    '''

    @wraps(func)
    def wrapper(*args, **kwargs):
        req, params = func(*args, **kwargs)
        retry_count = 3
        while retry_count > 0:
            try:
                res = requests.post(req, json=params, timeout=30,verify=False)
                break
            except requests.exceptions.ReadTimeout:
                print("retry:", retry_count)
                retry_count -= 1
            except Exception as e:
                traceback.print_exc()

        if retry_count <= 0:
            raise requests.exceptions.ReadTimeout

        # res.status_codemust be 2XX
        if res.status_code // 200 != 1:
            return False, res.text
        result = json.loads(res.content.decode('utf-8'))
        if type(result) == dict:
            return not result.get('error'), result
        else:
            return True, result

    return wrapper
