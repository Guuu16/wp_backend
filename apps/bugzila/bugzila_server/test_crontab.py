# -*- coding: utf-8 -*-
"""
@Time ： 1/18/23 5:01 PM
@Auth ： gujie5
"""
import datetime
import json
import os, django
import re

from django.core.cache import cache
from webportal import settings
from celery import shared_task

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webportal.settings')
django.setup()
from apps.bugzila.bugzila_server.bugzilawebservice import BugzillaWebService
from cache_helper import get_cache_or_exc_func
from django.db import connection
from bugzila.models import User as BugzilaUser
from machine.models import CommonConfigMessage
from apps.bugzila.bugzila_server.get_all_dev import Ldap3Util
from django.contrib.auth.models import User

url_base = "https://bz.labs.company.com"
token = "3546-t2iKyULbjn"


def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]


@shared_task
def bugs_redis(creation_time=settings.BUG_CREATE_TIME):
    cur = connection.cursor()
    cur.execute('select user from bugzila_user where auto_or_manual = "auto";')
    dic = dictfetchall(cur)
    lis = []
    for user in dic: lis.append(user["user"])
    bug = BugzillaWebService(url_base=url_base, token=token)
    res = bug.Search_Bugs(product=settings.SEARCH_PRODUCT, creator=lis, creation_time=creation_time, summary=["[CFB"])
    cache.set("auto", res, settings.NEVER_REDIS_TIMEOUT)
    cur.execute('select user from bugzila_user where auto_or_manual = "manual";')
    dic = dictfetchall(cur)
    lis = []
    for user in dic: lis.append(user["user"])
    # bug = BugzillaWebService(url_base=url_base, token=token)
    res = bug.Search_Bugs(product=settings.SEARCH_PRODUCT, creator=lis, creation_time=creation_time, summary=["[CFB"])
    cache.set("manual", res, settings.NEVER_REDIS_TIMEOUT)
    cur.execute('select user from bugzila_user where auto_or_manual = "xcc";')
    dic = dictfetchall(cur)
    lis = []
    for user in dic: lis.append(user["user"])
    bug = BugzillaWebService(url_base=url_base, token=token)
    res = bug.Search_Bugs(product=settings.SEARCH_PRODUCT, assigned_to=lis, creation_time=creation_time,
                          summary=["[CFB"])
    cache.set("xcc", res, settings.NEVER_REDIS_TIMEOUT)
    cur.execute('select user from bugzila_user where auto_or_manual = "uefi";')
    dic = dictfetchall(cur)
    lis = []
    for user in dic: lis.append(user["user"])
    bug = BugzillaWebService(url_base=url_base, token=token)
    res = bug.Search_Bugs(product=settings.SEARCH_PRODUCT, assigned_to=lis, creation_time=creation_time,
                          summary=["[CFB"])
    cache.set("uefi", res, settings.NEVER_REDIS_TIMEOUT)


@shared_task
def pa_qtester_redis(creation_time=settings.BUG_CREATE_TIME):
    bug = BugzillaWebService(url_base=url_base, token=token)
    res = bug.Search_Bugs(product=settings.SEARCH_PRODUCT, creation_time=creation_time, summary=["qtester", "Qtester"])
    cache.set("qtester", res, settings.NEVER_REDIS_TIMEOUT)


def add_bugzila_user():
    bugzila_user = CommonConfigMessage.objects.filter(CommonConfigName="bugzila_user")
    if bugzila_user:
        res = json.loads(bugzila_user[0].CommonConfig_message)
        for k, v in res.items():
            for i in v:
                try:
                    BugzilaUser.objects.get(user=i)
                    print(f"No need to add {i}")
                except BugzilaUser.DoesNotExist:
                    user = BugzilaUser()
                    user.user = i
                    user.auto_or_manual = k
                    user.save()
    print(f"update bugzila user done {datetime.datetime.now()}")


@shared_task
def get_all_workmate():
    common = CommonConfigMessage.objects.filter(CommonConfigName="common")
    res = json.loads(common[0].CommonConfig_message) if common else {}
    ldap_user = res.get('LDAP_server').get('username')
    ldap_password = res.get('LDAP_server').get('password')
    dic = {}
    manager_dict = settings.CORE_FW
    ldap = Ldap3Util.init_ldap(ldap_user, ldap_password)
    if ldap.auth_ldap():
        for k, manager_lis in manager_dict.items():
            dic[k] = []
            for manager in manager_lis:
                dic[k].append(f"{manager}@company.com")
                directReports_lis = ldap.search_ldap(manager)[1]['attributes']['directReports']
                for i in directReports_lis:
                    dic[k].append(f"{re.findall('CN=(.*?),OU', i)[0]}@company.com")
            dic[k] = list(set(dic[k]))
        print(dic)
        for k, v in dic.items():
            for i in v:
                try:
                    BugzilaUser.objects.get(user=i, auto_or_manual=k)
                    print(f"No need to add {i}")
                except BugzilaUser.DoesNotExist:
                    user = BugzilaUser()
                    user.user = i
                    user.auto_or_manual = k
                    user.save()
        print(f"update bugzila user done {datetime.datetime.now()}")


if __name__ == '__main__':
    get_all_workmate()
