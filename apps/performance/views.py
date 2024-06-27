import logging

import requests
from django.core.cache import cache
from django.shortcuts import render

# Create your views here.
import datetime
import json

from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.http import JsonResponse
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import View, APIView
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from apps.performance.perf.perf_test import Query, archive_cases_info, archive_hw_info, archive_sw_info, \
    achive_performance_info
from webportal import settings


def get_buildno(request):
    perf = json.loads(request.body.decode())
    buildno = perf.get("buildno")
    cache.set("buildno", buildno, settings.NEVER_REDIS_TIMEOUT)
    logging.info(f"get build number {buildno}")
    return JsonResponse({
        'response': "get buildno success",
        'code': "0000"
    })


def get_perf(request):
    try:
        perf = json.loads(request.body.decode())
        url = perf.get("url")
        resp = requests.get(url)
        result = resp.json()
        # case info first
        buildno = cache.get('buildno')
        result["JOB_ID"] = buildno
        archive_cases_info(result)
        archive_hw_info(result)
        archive_sw_info(result)
        achive_performance_info(result)
        return JsonResponse({
            'response': "get performance success",
            'code': "0000",
            "performance": result
        })
    except Exception as e:
        logging.error(e)
        return JsonResponse({
            'response': "get performance fail",
            "code": 9999
        }), 500


class Getplatform(APIView):
    authentication_classes = (JSONWebTokenAuthentication,)  # token认证
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return JsonResponse(Query().get_platform())


class Getcasemac(APIView):
    authentication_classes = (JSONWebTokenAuthentication,)  # token认证
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        perf = json.loads(request.body.decode())
        return JsonResponse(Query().get_case_mac_by_caseid(perf['platform']))


class Search(APIView):
    authentication_classes = (JSONWebTokenAuthentication,)  # token认证
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        dic = dict()
        perf = json.loads(request.body.decode())
        startdate = perf.get('startdate', None)
        enddate = perf.get('enddate', None)
        if startdate is not None:
            dic["start_date"] = datetime.datetime.strptime(startdate, '%Y-%m-%d')
        else:
            dic["start_date"] = ""
        if enddate is not None:
            end = enddate + " 23:59:59"
            dic["end_date"] = datetime.datetime.strptime(end, '%Y-%m-%d %H:%M:%S')
        else:
            dic["end_date"] = ""

        if startdate is not None and enddate is not None:
            if dic["start_date"] > dic["end_date"]:
                return JsonResponse({'code': '9999', "data": {"results": "incorrect date input ,please check"}}), 500
        dic['case_name_id'] = perf.get("testcases")
        dic["platform"] = perf.get("platform")
        if perf.get("hostMAC") == "all":
            dic["mac"] = ""
        else:
            dic["mac"] = perf.get("hostMAC")
        for k, v in dic.items():
            if v == "":
                dic[k] = None
        print(dic)
        search = Query().search(dic["start_date"], dic["end_date"], dic["case_name_id"], dic["platform"], dic["mac"])
        return JsonResponse(search)
