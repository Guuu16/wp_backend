# -*- coding: utf-8 -*-
"""
@Time ： 5/16/23 5:37 PM
@Auth ： gujie5
"""

import os, django, requests


from celery import shared_task
from django.core.cache import cache
from webportal import settings
from machine.models import HostInfo1 as HostInfo
from machine.models import HardWare1 as Hardware
from machine.models import ConfigMessage, CommonConfigMessage

from datetime import datetime

power_url = "/redfish/v1/Systems/1/"


@shared_task
def set_machine_status():
    dic = {}
    for host in HostInfo.objects.filter(Host_Status='0'):
        url = f"https://{host.IMMIP}{power_url}"
        header = {"Content-type": "application/json"}
        try:
            resp = requests.get(url=url, headers=header, auth=(host.IMMUSER, host.IMMPASSWORD),
                                verify=False, timeout=5)
            if resp.status_code == 200:
                res = resp.json()
                powerStatus = res.get('PowerState')
                dic[host.IMMIP] = powerStatus.lower()
        except requests.exceptions.ConnectTimeout:
            continue
        except Exception as e:
            print(e)
            continue
    cache.set("powerStatus", dic, settings.NEVER_REDIS_TIMEOUT)
