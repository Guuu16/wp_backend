# -*- coding: utf-8 -*-
"""
@Time ： 6/27/23 5:34 PM
@Auth ： gujie5
"""
# -*- coding: utf-8 -*-
import platform
import xml.etree.ElementTree as ET
from os import path

import base64
from datetime import datetime, timedelta


def bits_from(arr, base=2):
    res = 0
    if base == 2:
        for x in arr:
            if x < 0 or x > 1:
                raise ValueError(arr)
        for i in range(len(arr)):
            res += arr[~i] << i
    elif base == 10:
        for x in arr:
            if x < 0 or x > 9:
                raise ValueError(arr)
        b = 1
        for i in range(len(arr)):
            res += arr[~i] * b
            b *= 10
    return res


def weekdaysToInteger(weekdays):
    res = 0
    for w in weekdays:
        res += 1 << w
    return res


def get_clock_from(string):
    """
    for example:
    param string: "18:18"
    """
    nums = [int(x) for x in string if x != ':']
    print(nums)
    x = bits_from(nums, base=10)

    hour, minute = 0, 0
    b = 1
    for _ in range(2):
        minute = minute + x % 10 * b
        b *= 10
        x //= 10
    b = 1
    for _ in range(2):
        hour = hour + x % 10 * b
        b *= 10
        x //= 10
    return hour, minute


def get_weekdays_from_bits(w):
    res = []
    cur = 0
    while w != 0:
        if w & 1:
            res.append(cur)
        w >>= 1
        cur += 1
    return res


def has_weekday(w, weekday):
    cur = 0
    while w != 0:
        if w & 1 and weekday == cur:
            return True
        cur += 1
        w >>= 1
    return False


def getScheduletime(allow_weekdays, string='', dateobj=None):
    if string:
        hour, minute = get_clock_from(string)
    elif dateobj is not None:
        hour, minute = dateobj.hour, dateobj.minute
    else:
        raise ValueError([string, dateobj])
    now = datetime.now()
    nextTime = datetime(now.year, now.month, now.day, hour, minute)
    if nextTime < now or not has_weekday(allow_weekdays, nextTime.weekday()):
        for i in range(7):
            nextTime += timedelta(days=1)
            if has_weekday(allow_weekdays, nextTime.weekday()):
                break
    print(nextTime)
    return nextTime


