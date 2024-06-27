import datetime
import json
import re
import logging
import jenkins
import jwt
import ldap
import requests
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.http import JsonResponse
from rest_framework.generics import get_object_or_404
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from django.forms.models import model_to_dict
from rest_framework.permissions import IsAuthenticated
from rest_framework_jwt.settings import api_settings
from rest_framework.views import View, APIView
# from django.shortcuts import JsonResponse, render
from webportal import settings, util
from django.core.cache import cache
from jenkinsServer.models import Task2 as Task
from jenkinsServer.models import Group
from jenkinsServer.models import Host
from jenkinsServer.models import TaskEmailDetail
from jenkinsServer.models import StressTask
from loginAndLogout.models import Eventlog
from jenkinsServer.models import TaskSchedule
from apps.jenkinsServer.jenkins_server.tasks import sync_jenkins_jobs, opt_job, option_job
from apps.jenkinsServer.jenkins_server.jenkins_backend import getServer
import collections
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)


# response_data = {"msg": "success", "data": {}}


class CustomResponse(Response):
    def __init__(self, data=None, msg=None, status=None, template_name=None, headers=None, exception=False,
                 content_type=None, **kwargs):
        super().__init__(None, status=status)
        if isinstance(data, Serializer):
            msg = (
                'You passed a Serializer instance as data, but '
                'probably meant to pass serialized `.data` or '
                '`.error`. representation.'
            )
            raise AssertionError(msg)
            # 自定义返回格式
        self.data = {'msg': msg, 'data': data}
        self.data.update(kwargs)
        self.template_name = template_name
        self.exception = exception
        self.content_type = content_type
        if headers:
            for name, value in headers.items():
                self[name] = value


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return json.JSONEncoder.default(self, obj)


class UtilMixin(object):
    def get_entry_url(self, jobname, buildno):
        if r"/" in jobname:
            folder, subjobname = jobname.split("/")
            url = settings.JENKINS_URL + \
                  "/blue/rest/organizations/jenkins/pipelines/{folder}/pipelines/{subjobname}/runs/{buildno}/nodes/?limit=10000".format(
                      **locals())
        else:
            url = settings.JENKINS_URL + \
                  "/blue/rest/organizations/jenkins/pipelines/{jobname}/runs/{buildno}/nodes/?limit=10000".format(
                      **locals())
        logger.warning(url)
        return url

    def getParamsFromJSON(self, jsonstr, jobname):
        p, release, suffix = jobname.split('/')[-1].split('_', 2)
        if not jsonstr: return []
        res = collections.OrderedDict()
        res["product"] = p
        res["release"] = release
        jd = collections.OrderedDict(json.loads(jsonstr))
        systemNames = []
        systems = []
        testItems = []
        res["sender"] = jd["SENDER"]
        res["receiver"] = jd["RECEIVER"]
        if suffix == "daily" or p == 'daily':
            res["source"] = "daily"
            for k, v in jd.items():
                if (k.endswith("_XTEST") or k.endswith("_UTEST")) and v:
                    testItems.append(k[:~5])
                elif k.endswith("_SYS") and v:
                    systemNames.append(k[:~3])
        elif p == "mrt":
            res['source'] = 'mrt'
            for k, v in jd.items():
                if (k.endswith("_XTEST") or k.endswith("_UTEST") or k.endswith("_STEST")) and v != 0:
                    testItems.append(k[:~5])
        elif p == "memorystress":
            res["source"] = "memorystress"
            for k, v in jd.items():
                if k.endswith("_MTEST") and v:
                    testItems.append(k[:~5])
                elif k.endswith("_SYS") and v:
                    systemNames.append(k[:~3])
        elif p == "xpit":
            res['source'] = "xpit"
            for k, v in jd.items():
                if k.endswith("_STEST") and int(v) > 0:
                    if "loop" not in res: res["loop"] = v
                    testItems.append(k[:~5])
                elif k.endswith("_SYS") and v:
                    systemNames.append(k[:~3])
        elif p == "performance":
            res['source'] = "performance"
            for k, v in jd.items():
                if k.endswith("_PTEST") and int(v) > 0:
                    if "loop" not in res: res["loop"] = v
                    testItems.append(k[:~5])
                elif k.endswith("_SYS") and v:
                    systemNames.append(k[:~3])
        if testItems: res["testItems"] = testItems
        configdict = {}
        if "BUILD_CFG" in jd:
            _build_config = jd["BUILD_CFG"]
            # replace \" to "
            build_config = _build_config.replace('\\"', '"')
            configdict = json.loads(build_config)
        for name in systemNames:
            systems.append({"name": name, "builds": configdict.get(name, [])})
        if systems: res["systems"] = systems
        return res

    def setExternalTaskscheduler(self, taskdict):
        taskdict["weekdays"] = [{"id": wid, "text": settings.WEEKDAYS[wid]} for wid in
                                util.get_weekdays_from_bits(taskdict["weekdays"])]
        taskdict["clock"] = "%02d:%02d" % (taskdict["schedule_time"].hour, taskdict["schedule_time"].minute)


class ApiJobs(APIView):
    authentication_classes = (JSONWebTokenAuthentication,)  # token认证
    permission_classes = (IsAuthenticated,)

    def get(self, request, job):
        if job == "xpit":
            options = option_job(cache.get("jobs"), "xpit")
            # response_data["data"] = options
            return CustomResponse(data=options, msg="success")
        elif job == "daily":
            options = option_job(cache.get("jobs"), "daily")
            # print(options)
            # for i in range(len(options['releaseOptions'])):
            #     id = options['releaseOptions'][i]['id'].split("_")[1]
            #     options['releaseOptions'][i]['id'] = id
            return CustomResponse(data=options, msg="success")
        elif job == "UEFI":
            options = option_job(cache.get("jobs"), "UEFI")
            return CustomResponse(data=options, msg="success")
        elif job == "mrt":
            options = option_job(cache.get("jobs"), "mrt")
            return CustomResponse(data=options, msg="success")
        elif job == "stress":
            options = option_job(cache.get("jobs"), "memorystress")
            return CustomResponse(data=options, msg="success")
        elif job == "performance":
            options = option_job(cache.get("jobs"), "performance")
            return CustomResponse(data=options, msg="success")
        else:
            return CustomResponse(data="no data", msg="fail")


class ApiTaskTrigger(APIView):
    authentication_classes = (JSONWebTokenAuthentication,)  # token认证
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        username = request.session.get("username")
        jd = json.loads(request.body.decode())
        self.source = int(jd.get("source", 0))
        if not jd:
            jd = json.loads(request.get_data())
        jobnum = len(jd['params']['systems'])

        # get immip
        jobname = self.get_job_fullname(jd, jobnum)
        print(jobname)
        immip_list = []
        for jb in jobname:
            immip_list += self.get_child_immip(jb, self.source)
        res = {"success": True}
        commoninfo = dict()
        user = User.objects.get(username=username, is_active=1)
        commoninfo['username'] = user.username
        commoninfo['userid'] = user.username
        commoninfo["release"] = jd["release"]
        commoninfo["source"] = self.source
        commoninfo['result'] = "START"
        logger.warning(jobname)
        server = getServer()
        jobname_lis = self.get_job_fullname(jd, jobnum)
        for jobname in jobname_lis:
            num = 0
            if self.source == 2:
                params = self.handle_mrt_params(jd, username, num)
            elif self.source == 1:
                params = self.handle_daily_params(jd, username, num)
            elif self.source == 0:
                params = self.handle_xpit_params(jd, username, num)
            elif self.source == 3:
                params = self.handle_stress_params(jd, username, num)
            elif self.source == 4:
                params = self.handle_uefi_params(jd, username)
            elif self.source == 5:
                params = self.handle_performance_params(jd, username, num)
                # logger.warning(params)
            if jd.get("schedule"):
                scheduleData = jd["schedule"]
                # fields: clock 11:11, total 1, weekdays[{"id":0, "text": "Sun"}]
                weekdays = util.weekdaysToInteger(w["id"] for w in scheduleData["weekdays"])
                print(weekdays)
                tser = TaskSchedule()
                tser.jobname = jobname
                tser.weekdays = weekdays
                tser.schedule_time = util.getScheduletime(weekdays, scheduleData["clock"])
                tser.total = scheduleData["loop"] * len(scheduleData["weekdays"])
                tser.userid = User.objects.get(username=username)
                tser.username = commoninfo["username"]
                tser.source = commoninfo["source"]
                tser.release = commoninfo["release"]
                tser.params = json.dumps(params)
                tser.save()
                event = Eventlog()
                event.events = f"{username} create schedule: trigger {jobname} "
                event.result = "success"
                event.userid = User.objects.get(username=username)
                event.save()
                # res = {"success": False, "error": msg}
                return CustomResponse(data=res, msg="success")
            else:
                buildNumber, msg = server.buildJob(jobname, params)
                if buildNumber < 0:
                    event = Eventlog()
                    event.events = f"{username} trigger {jobname} build_number: {buildNumber} "
                    event.result = "fail"
                    event.userid = User.objects.get(username=username)
                    event.save()
                    res = {"success": False, "error": msg}
                    return CustomResponse(data=res, msg="fail", status=500)
                else:
                    buildInfo = server.get_build_info(jobname, buildNumber)
                    buildInfo.update(commoninfo)
                    task = Task()
                    task.jobname = jobname
                    task.build_number = buildNumber
                    task.building = buildInfo["building"]
                    task.url = settings.JENKINS_URL + buildInfo["url"].split("/", 3)[-1]
                    task.result = buildInfo["result"]
                    task.username = buildInfo["username"]
                    task.userid = buildInfo["userid"]
                    task.release = buildInfo["release"]
                    task.source = buildInfo["source"]
                    task.params = json.dumps(params)
                    task.save()
                    if immip_list:
                        for i in immip_list:
                            host = Host()
                            host.immip = list(i.values())[0]
                            host.build_number = Task.objects.filter(build_number=buildNumber, source=self.source,
                                                                    jobname=jobname).order_by('-createtime')[0]
                            host.save()
                    # echo_message("Trigger Task: %s(#%s)" % (jobname, buildNumber))
                    # response_data['data'] = res
                    event = Eventlog()
                    event.events = f"{username} trigger {jobname} build_number: {buildNumber}"
                    event.result = "success"
                    event.userid = User.objects.get(username=username)
                    event.save()
            num += 1
        return CustomResponse(data=res, msg="success")

    def get_job_fullname(self, jd, jobnum=1):
        key = {0: "xpit", 1: "daily", 2: "mrt", 3: "memorystress", 4: "UEFI", 5: 'performance'}[self.source]
        jobs = cache.get("jobs")[key]
        full_num_lis = []
        for job in jobs:
            if self.source == 0:
                for i in range(jobnum):
                    full_num_lis.append(job['fullname']) if job[
                                                                'name'] == f"xpit_{jd['release']}_{jd['params']['systems'][i]['name']}" else full_num_lis
            if self.source == 1:
                for i in range(jobnum):
                    full_num_lis.append(job['fullname']) if job[
                                                                'name'] == f"daily_{jd['release']}_{jd['params']['systems'][i]['name']}" else full_num_lis
            if self.source == 3:
                for i in range(jobnum):
                    full_num_lis.append(job['fullname']) if job[
                                                                'name'] == f"memorystress_{jd['release']}_{jd['params']['systems'][i]['name']}" else full_num_lis
            if self.source == 4:
                for i in range(jobnum):
                    full_num_lis.append(job['fullname']) if job[
                                                                'name'] == f"uefi_{jd['release']}_{jd['params']['systems'][i]['name']}" else full_num_lis
            if self.source == 5:
                for i in range(jobnum):
                    full_num_lis.append(job['fullname']) if job[
                                                                'name'] == f"performance_{jd['release']}_{jd['params']['systems'][i]['name']}" else full_num_lis
            if self.source == 2:
                for i in range(jobnum):
                    full_num_lis.append(job['fullname']) if job[
                                                                'name'] == f"mrt_{jd['release']}_{jd['params']['systems'][i]['name']}" else full_num_lis
        return full_num_lis

    def getValidBuild(self, system):
        # oss, daily, files
        res = []
        for b in system["builds"]:
            if b["buildtype"] == "oss" and b["ossid"].strip():
                res.append(b)
            elif b["buildtype"] == "daily":
                res.append(b)
            elif b['buildtype'] == 'drum' and b['drum']:
                res.append(b)
            elif b["buildtype"] == "files" and b["files"]:
                res.append(b)
        return res

    def get_group_receivers(self, recevier, group):
        if group is False: return recevier
        mail_pattern = re.compile(r'[0-9a-zA-z]+@company.com')
        mails = mail_pattern.findall(group.members)
        return ','.join(set([recevier] + mails))

    def handle_mrt_params(self, jd, username, num=0):
        res = collections.OrderedDict()
        params = jd["params"]
        jobs = cache.get("jobs")["mrt"]
        # handle systems
        buildInfo = {}
        for system in params['systems']:
            # res['%s_SYS' % system['name']] = True
            vbuilds = self.getValidBuild(system)
            if vbuilds:
                buildInfo[system["name"]] = vbuilds

        if buildInfo:
            _build_config = json.dumps(buildInfo)
            # replace " to \"
            build_config = _build_config.replace('"', '\\"')
            res["BUILD_CFG"] = build_config

        try:
            group = Group.objects.get(id=jd["groupId"])
        except Group.DoesNotExist:
            group = False
        res['RECEIVER'] = self.get_group_receivers(recevier=f"{username}@company.com", group=group)
        res['SENDER'] = f"{username}@company.com"

        # handle testItems
        xccTestItemSet = set(params["testItems"]['xcc'])
        uefiTestItemSet = set(params["testItems"]['uefi'])
        stressTestItemSet = set(params['testItems']['stress'])
        # uefi test endswith 'UTEST'
        # xcc test endswith 'XTEST'
        # xpit_19a_constantine_207_entry
        target = None
        # print(jobs)
        for job in jobs:
            if job['name'].startswith('mrt_') and job['name'].split("_")[1] == jd["release"] and \
                    jd["params"]['systems'][num]['name'] == job['name'].split("_", 2)[-1]:
                target = job
                break
        for param in target['params']:
            pname = param['name']
            logger.warning(pname)
            nameset = {system['name'] for system in params['systems']}
            logger.warning(nameset)
            if pname.endswith("_SYS") and pname[:~3] not in nameset:
                res[pname] = False
            if pname.endswith("_UTEST"):
                res[pname] = 1 if pname[:~5] in uefiTestItemSet else 0
            if pname.endswith("_DOCKER") or pname == "DRAFT":
                res[pname] = True if pname in xccTestItemSet else False
            elif pname.endswith("_XTEST"):
                res[pname] = 1 if pname[:~5] in xccTestItemSet else 0
            elif pname.endswith("_STEST") and "loop" in params:
                res[pname] = 1 if pname[:~5] in stressTestItemSet else 0
            elif pname == "LOOP":
                res[pname] = params['loop']
            if pname[:~5].endswith("Loops"):
                # PowerCycleLoops_XTEST
                k = pname[:~5]
                if k in params["loops"]:
                    res[pname] = int(params["loops"][k])
                else:
                    res.pop(pname)
        return res

    def handle_daily_params(self, jd, username, num=0):
        res = collections.OrderedDict()
        params = jd["params"]
        jobs = cache.get("jobs")["daily"]
        # handle systems
        buildInfo = {}
        for system in params['systems']:
            res['%s_SYS' % system['name']] = True
            vbuilds = self.getValidBuild(system)
            if vbuilds:
                buildInfo[system["name"]] = vbuilds

        if buildInfo:
            _build_config = json.dumps(buildInfo)
            # replace " to \"
            build_config = _build_config.replace('"', '\\"')
            res["BUILD_CFG"] = build_config

        # group = Group.query.get_or_404(jd["groupId"])
        # res['RECEIVER'] = self.get_group_receivers(group)
        # res['SENDER'] = session["mail"]
        # res['RECEIVER'] = f"{username}@company.com"
        try:
            group = Group.objects.get(id=jd["groupId"])
        except Group.DoesNotExist:
            group = False
        res['RECEIVER'] = self.get_group_receivers(recevier=f"{username}@company.com", group=group)
        res['SENDER'] = f"{username}@company.com"

        # handle testItems
        xccTestItemSet = set(params["testItems"]['xcc'])
        uefiTestItemSet = set(params["testItems"]['uefi'])
        # uefi test endswith 'UTEST'
        # xcc test endswith 'XTEST'
        # xpit_19a_constantine_207_entry
        target = None
        for job in jobs:
            if job['name'].startswith('daily_') and job['name'].split("_")[1] == jd["release"] and \
                    jd["params"]['systems'][num]['name'] == job['name'].split("_", 2)[-1]:
                target = job
                break
        for param in target['params']:
            pname = param['name']
            logger.warning(pname)
            nameset = {system['name'] for system in params['systems']}
            logger.warning(nameset)
            if pname.endswith("_SYS") and pname[:~3] not in nameset:
                res[pname] = False
            if pname.endswith("_UTEST"):
                res[pname] = 1 if pname[:~5] in uefiTestItemSet else 0
            if pname.endswith("_DOCKER") or pname == "DRAFT":
                res[pname] = True if pname in xccTestItemSet else False
            elif pname.endswith("_XTEST"):
                res[pname] = 1 if pname[:~5] in xccTestItemSet else 0
            if pname[:~5].endswith("Loops"):
                # PowerCycleLoops_XTEST
                k = pname[:~5]
                if k in params["loops"]:
                    res[pname] = int(params["loops"][k])
                else:
                    res.pop(pname)
        return res

    def handle_uefi_params(self, jd, username):
        res = collections.OrderedDict()
        params = jd["params"]
        jobs = cache.get("jobs")["UEFI"]
        # handle systems
        buildInfo = {}
        for system in params['systems']:
            res['%s_SYS' % system['name']] = True
            vbuilds = self.getValidBuild(system)
            if vbuilds:
                buildInfo[system["name"]] = vbuilds

        if buildInfo:
            _build_config = json.dumps(buildInfo)
            # replace " to \"
            build_config = _build_config.replace('"', '\\"')
            res["BUILD_CFG"] = build_config
        # todo: upload, oss
        #
        # group = Group.query.get_or_404(jd["groupId"])
        # res['RECEIVER'] = self.get_group_receivers(group)
        # res['SENDER'] = session["mail"]
        # res['RECEIVER'] = f"{username}@company.com"
        try:
            group = Group.objects.get(id=jd["groupId"])
        except Group.DoesNotExist:
            group = False
        res['RECEIVER'] = self.get_group_receivers(recevier=f"{username}@company.com", group=group)
        res['SENDER'] = f"{username}@company.com"
        # raise Exception(res)
        #
        testItemSet = set(params["testItems"])
        # xpit_19a_constantine_207_entry
        target = None
        for job in jobs:
            _, release, product = job['name'].split('_', 2)
            if release == jd['release'] and product == jd['p']:
                target = job
                break
        for param in target['params']:
            pname = param['name']
            nameset = {system['name'] for system in params['systems']}
            if pname.endswith("_SYS") and pname[:~3] not in nameset:
                res[pname] = False
            if pname.endswith("_TEST"):
                res[pname] = pname[:~4] in testItemSet
        return res

    def handle_xpit_params(self, jd, username, num=0):
        res = collections.OrderedDict()
        params = jd["params"]
        jobs = cache.get("jobs")["xpit"]
        # handle systems
        buildInfo = {}
        for system in params['systems']:
            res['%s_SYS' % system['name']] = True
            vbuilds = self.getValidBuild(system)
            if vbuilds:
                buildInfo[system["name"]] = vbuilds

        if buildInfo:
            _build_config = json.dumps(buildInfo)
            # replace " to \"
            build_config = _build_config.replace('"', '\\"')
            res["BUILD_CFG"] = build_config
        # todo: upload, oss
        #
        # group = Group.query.get_or_404(jd["groupId"])
        # res['RECEIVER'] = self.get_group_receivers(group)
        # res['SENDER'] = session["mail"]
        # res['RECEIVER'] = f"{username}@company.com"
        try:
            group = Group.objects.get(id=jd["groupId"])
        except Group.DoesNotExist:
            group = False
        res['RECEIVER'] = self.get_group_receivers(recevier=f"{username}@company.com", group=group)
        res['SENDER'] = f"{username}@company.com"
        # raise Exception(res)
        #
        if "loop" in params:
            testItemSet = set(params["testItems"])
            # xpit_19a_constantine_207_entry
            target = None
            for job in jobs:
                if job['name'].startswith('xpit_') and job['name'].split("_")[1] == jd["release"] and \
                        jd["params"]['systems'][num]['name'] == job['name'].split("_", 2)[-1]:
                    target = job
                    break
            for param in target['params']:
                pname = param['name']
                nameset = {system['name'] for system in params['systems']}
                if pname.endswith("_SYS") and pname[:~3] not in nameset:
                    res[pname] = False
                elif pname.endswith('_DOCKER') or pname == "DRAFT":
                    res[pname] = pname in testItemSet
                elif pname.endswith("_STEST") and "loop" in params:
                    res[pname] = 1 if pname[:~5] in testItemSet else 0
                elif pname == "LOOP":
                    res[pname] = params['loop']
        return res

    def handle_performance_params(self, jd, username, num=0):
        res = collections.OrderedDict()
        params = jd["params"]
        jobs = cache.get("jobs")["performance"]
        # handle systems
        buildInfo = {}
        for system in params['systems']:
            res['%s_SYS' % system['name']] = True
            vbuilds = self.getValidBuild(system)
            if vbuilds:
                buildInfo[system["name"]] = vbuilds

        if buildInfo:
            _build_config = json.dumps(buildInfo)
            # replace " to \"
            build_config = _build_config.replace('"', '\\"')
            res["BUILD_CFG"] = build_config
        # todo: upload, oss
        #
        # group = Group.query.get_or_404(jd["groupId"])
        # res['RECEIVER'] = self.get_group_receivers(group)
        # res['SENDER'] = session["mail"]
        # res['RECEIVER'] = f"{username}@company.com"
        try:
            group = Group.objects.get(id=jd["groupId"])
        except Group.DoesNotExist:
            group = False
        res['RECEIVER'] = self.get_group_receivers(recevier=f"{username}@company.com", group=group)
        res['SENDER'] = f"{username}@company.com"
        # raise Exception(res)
        #
        if "loop" in params:
            testItemSet = params["testItems"]
            # xpit_19a_constantine_207_entry
            target = None
            for job in jobs:
                if job['name'].startswith('performance_') and job['name'].split("_")[1] == jd["release"] and \
                        jd["params"]['systems'][num]['name'] == job['name'].split("_", 2)[-1]:
                    target = job
                    break
            for param in target['params']:
                pname = param['name']
                nameset = {system['name'] for system in params['systems']}
                if pname.endswith("_SYS") and pname[:~3] not in nameset:
                    res[pname] = False
                elif pname.endswith('_DOCKER') or pname == "DRAFT":
                    res[pname] = pname in testItemSet
                elif pname.endswith("_PTEST") and "loop" in params:
                    res[pname] = 1 if pname[:~5] in testItemSet else 0
                elif pname == "LOOP":
                    res[pname] = params['loop']
            logger.warning(res)
        return res

    def handle_stress_params(self, jd, username, num=0):
        res = collections.OrderedDict()
        params = jd["params"]
        jobs = cache.get("jobs")["memorystress"]
        # handle systems
        buildInfo = {}
        for system in params['systems']:
            res['%s_SYS' % system['name']] = True
            vbuilds = self.getValidBuild(system)
            if vbuilds:
                buildInfo[system["name"]] = vbuilds

        if buildInfo:
            _build_config = json.dumps(buildInfo)
            # replace " to \"
            build_config = _build_config.replace('"', '\\"')
            res["BUILD_CFG"] = build_config
        # todo: upload, oss
        #
        # group = Group.query.get_or_404(jd["groupId"])
        # res['RECEIVER'] = self.get_group_receivers(group)
        # res['SENDER'] = session["mail"]
        # res['RECEIVER'] = f"{username}@company.com"
        try:
            group = Group.objects.get(id=jd["groupId"])
        except Group.DoesNotExist:
            group = False
        res['RECEIVER'] = self.get_group_receivers(recevier=f"{username}@company.com", group=group)
        res['SENDER'] = f"{username}@company.com"
        # raise Exception(res)
        res["TimeOut"] = int(params["hours"]) * 3600
        # if "loop" in params:
        testItemSet = set(params["testItems"])
        # xpit_19a_constantine_207_entry
        target = None
        for job in jobs:
            if job['name'].startswith('memorystress_') and job['name'].split("_")[1] == jd["release"] and \
                    jd["params"]['systems'][num]['name'] == job['name'].split("_", 2)[-1]:
                target = job
                break
        for param in target['params']:
            pname = param['name']
            nameset = {system['name'] for system in params['systems']}
            if pname.endswith("_SYS") and pname[:~3] not in nameset:
                res[pname] = False
            if pname.endswith("_MTEST"):
                res[pname] = pname[:~3] in testItemSet
        for param in target['params']:
            pname = param['name']
            nameset = {system['name'] for system in params['systems']}
            if pname.endswith("_SYS") and pname[:~3] not in nameset:
                res[pname] = False
            if pname.endswith('_DOCKER') or pname == "DRAFT":
                res[pname] = pname in testItemSet
            elif pname.endswith("_MTEST"):
                res[pname] = 1 if pname[:~5] in testItemSet else 0
        return res

    def get_immip(self, jd, jobname, source):
        server = getServer()
        lis, immip = [], []
        if source == 5 or source == 0:
            childjob = jobname[:~5]
        else:
            qian, hou = jobname.split("/")[0], jobname.split("/")[1]
            childjob = f"{qian}/{hou.split('_')[2]}_{hou.split('_')[1]}"
        for i in jd['params']['systems']:
            lis.append(f"{childjob}_{i['name'].lower()}")
            lis.append(f"{childjob}_{i['name'].capitalize()}")
        for jb in lis:
            try:
                buildInfo = server.get_job_info(jb)
            except jenkins.JenkinsException:
                continue
            logger.warning(buildInfo)
            for i in buildInfo['property']:
                if 'parameterDefinitions' in i:
                    for j in i['parameterDefinitions']:
                        if "defaultParameterValue" in j and j['defaultParameterValue']["name"] == "IMMIP":
                            immip.append({jb: j['defaultParameterValue']['value']})
        logger.warning(immip)
        return immip

    def get_child_immip(self, jobname, source):
        server = getServer()
        immip = []
        try:
            buildInfo = server.get_job_info(jobname)
            logger.warning(buildInfo)
            for i in buildInfo['property']:
                if 'parameterDefinitions' in i:
                    for j in i['parameterDefinitions']:
                        if "defaultParameterValue" in j and j['defaultParameterValue']["name"] == "IMMIP":
                            immip.append({jobname: j['defaultParameterValue']['value']})
            return immip
        except jenkins.JenkinsException:
            return immip


class ApiTask(APIView, UtilMixin):
    authentication_classes = (JSONWebTokenAuthentication,)  # token认证
    permission_classes = (IsAuthenticated,)

    # decorators=[util.request_remote]

    def get_systems(self, task):
        res = []
        if task["params"]:
            jd = collections.OrderedDict(json.loads(task["params"]))
            for k in jd:
                if k.endswith('_SYS') and jd[k]:
                    res.append(k[:~3])
        return res

    def get(self, request):
        # task history arrange by release
        # group by release
        request.encoding = 'utf-8'
        source = 0
        source = int(request.GET["source"]) if "source" in request.GET else source
        # source = int(jd.get("source", 0))
        tasklist = []
        for task in Task.objects.filter(source=source).order_by('-updatetime'):
            logger.warning(task)
            duration = task.updatetime - task.createtime
            taskdict = model_to_dict(task)
            taskdict["duration"] = duration.seconds
            tasklist.append(taskdict)
        temp = collections.OrderedDict()
        for t in tasklist:
            t['systems'] = self.get_systems(t)
            t["params"] = self.getParamsFromJSON(t["params"], t["jobname"])
            # if t['systems']: t['building']=True
            t_release = t["release"]
            if t_release in temp:
                if len(temp[t_release]) < 6:
                    temp[t_release].append(t)
            else:
                temp[t_release] = [t]
        data = []
        for release, tasks in temp.items():
            one = {"release": release, "tasks": tasks}
            data.append(one)
        # response_data['data'] = data
        return CustomResponse(data=data, msg="success")


class ApiTaskDetail(APIView, UtilMixin):
    authentication_classes = (JSONWebTokenAuthentication,)  # token认证
    permission_classes = (IsAuthenticated,)

    def getDetailUrl(self, task, params):
        # /blue/rest/organizations/jenkins/pipelines/xPITCustomization/pipelines/xpit_m1_sr950_128/runs/76/
        # /blue/rest/organizations/jenkins/pipelines/xcc_19b_daily/runs/518/
        systems = params.get("systems", [])
        resp = requests.get(self.get_entry_url(task.jobname, task.build_number))
        res = {}
        # if task.source == 0:
        try:
            for node in resp.json():
                actions = node["actions"]
                if actions:
                    href = actions[0]["link"]["href"]
                    frag = [x for x in href.split('/') if x.strip()]
                    folder = frag[~4 if href.count("pipelines") == 2 else ~2]
                    subjobname, buildno = frag[~2], frag[~0]
                    full_jobname = "{folder}%2F{subjobname}".format(**locals())
                    nodename = 'na'
                    for syst in systems:
                        if node["displayName"].endswith(syst['name'].lower()) or \
                                node["displayName"].lower() == syst['name'].lower():
                            nodename = syst['name']
                            break
                    res[
                        nodename] = settings.JENKINS_URL + "blue/organizations/jenkins/{full_jobname}/detail/{subjobname}/{buildno}/pipeline".format(
                        **locals())
            else:
                full_jobname, subjobname, buildno = task.jobname.replace("/", "%2F"), task.jobname.split("/")[
                    1], task.build_number

                res[
                    "na"] = settings.JENKINS_URL + "blue/organizations/jenkins/{full_jobname}/detail/{subjobname}/{buildno}/pipeline".format(
                    **locals())
        except Exception as e:
            pass
        try:
            res["childjob"] = []
            # child_job_list = resp.json()[1:]
            child_job_list = resp.json()
            for i in range(len(child_job_list)):
                if child_job_list[i]['displayName'] == "SendEmail":
                    del child_job_list[i]
            child_job_list = child_job_list[1:]
            for child_job in child_job_list:
                displayName = child_job["displayName"].replace("/", "%2F")
                res["childjob"].append(
                    settings.JENKINS_URL + f'blue/organizations/jenkins/{child_job["displayName"].replace("/", "%2F")}/detail/{child_job["displayName"].split("/")[-1]}/{child_job["actions"][0]["link"]["href"].split("/")[-2]}/pipeline')
        except Exception as e:
            logger.warning(e)
        return res

    def get(self, request, id):

        task = Task.objects.get(id=id)
        if task:
            logger.warning(task)
            duration = task.updatetime - task.createtime
            taskdict = model_to_dict(task)
            emaildetail = TaskEmailDetail.objects.filter(taskid=task.id).first()
            if emaildetail:
                taskdict['emaildetail'] = json.loads(emaildetail.emaildetail)
            else:
                taskdict['emaildetail'] = {}
            taskdict["duration"] = duration.seconds
            taskdict["params"] = self.getParamsFromJSON(taskdict["params"], task.jobname)
            print(taskdict.get('build_number'))
            print(taskdict["params"].get("systems"))
            taskdict["urls"] = self.getDetailUrl(task, taskdict["params"])
            print(taskdict["urls"])
            res = {"success": True, "task": taskdict}
            # response_data['data'] = res
            return CustomResponse(data=res, msg="success")

    def post(self, request, id):
        task = Task.objects.get(id=id)
        if task:
            jd = json.loads(request.body.decode())
            if jd["action"] == "stop":
                jobname, buildNumber = task.jobname, task.build_number
                server = getServer()
                server.stop_build(jobname, buildNumber)
                Task.objects.filter(id=id).update(building=False, result="ABORTED",
                                                  updatetime=datetime.datetime.now())
                res = {"success": True}
                return CustomResponse(data=res, msg="success")


class ApiTaskStages(APIView, UtilMixin):
    authentication_classes = (JSONWebTokenAuthentication,)  # token认证
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        '''
        How to Get Build Stages Info?
        Use API Blueocean Provided
        steps:
        1. concat url
        http://fw.core.company.com:8080/jenkins/blue/rest/organizations/jenkins/pipelines/xPITCustomization/pipelines/xpit_m1_sr950_128/runs/76/
        '''
        # blue/rest/organizations/jenkins/pipelines/xPITCustomization/pipelines/xpit_customization_entry/runs/80/nodes/?limit=10000
        jobname = request.GET.get("jobname")
        buildno = request.GET.get("buildno")
        source = 0
        source = int(request.GET.get("source")) if "source" in request.GET else source
        # source = request.GET.get("source", 0, type=int)
        # source = 0
        resp = requests.get(self.get_entry_url(jobname, buildno))
        res = []
        # if "mrt" in jobname:
        lis = jobname.split("/")
        res.append({"nodes": resp.json()})
        res[0][
            'childjob'] = settings.JENKINS_URL + f'blue/organizations/jenkins/{lis[0]}%2F{lis[-1]}/detail/{lis[-1]}/{buildno}/pipeline'
        return CustomResponse(data=res, msg="success")
        # resp = requests.get(settings.JENKINS_URL + resp.json()[0]['_links']['steps']['href'])
        # task = Task.objects.filter(jobname=jobname, build_number=int(buildno), source=source).first()
        # if task:
        #     params = self.getParamsFromJSON(task.params, task.jobname)
        #     systems = params.get("systems", [])
        #     for node in resp.json():
        #         actions = node["actions"]
        #         if actions and len(actions) == 2:
        #             logger.warning(actions)
        #             act = actions[1]
        #             logger.warning(settings.JENKINS_URL + act["link"]["href"] + 'nodes')
        #             resp = requests.get(settings.JENKINS_URL + act["link"]["href"] + 'nodes')
        #             logger.warning(resp.json())
        #             nodename = 'na'
        #             for syst in systems:
        #                 if node["displayName"].endswith(syst['name'].lower()) or \
        #                         node["displayName"].lower() == syst['name'].lower():
        #                     nodename = syst['name']
        #                     break
        #             res.append({"displayName": nodename, "nodes": resp.json()})
        #     try:
        #         child_job_list = requests.get(self.get_entry_url(jobname, buildno)).json()
        #         child_step = child_job_list[0]['_links']['steps']['href']
        #         resp = requests.get(settings.JENKINS_URL + child_step).json()
        #         if len(resp) > 1:
        #             displayname = resp[-1]['displayName']
        #             lis = displayname.split(" ")
        #             num = resp[-1]['actions'][-1]['link']['href'].split("/")[-2]
        #             print(num)
        #             res[0][
        #                 'childjob'] = settings.JENKINS_URL + f'blue/organizations/jenkins/{lis[1]}%2F{lis[-1]}/detail/{lis[-1]}/{num}/pipeline'
        #     except Exception as e:
        #         logger.warning(e)

        # return CustomResponse(data=res, msg="success")


def allowed_file(filename):
    # logger.warning(filename)
    # ALLOWED_EXTENSIONS = ['uxz', 'upd', 'xml', 'zip']
    if '.' in filename and filename.split('.')[-1].lower() in settings.ALLOWED_EXTENSIONS:
        return True
    else:
        return False


class UploadFile(APIView):
    authentication_classes = (JSONWebTokenAuthentication,)  # token认证
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            params = {
                "release": request.GET.get("release"),
                "system": request.GET.get("system"),
                "product": request.GET.get("product"),
            }
            if 'file' not in request.FILES:
                return CustomResponse(data="no file", msg="fail", status=404)

            file = request.FILES['file']
            logger.warning(file)
            # if user does not select file, browser also
            # submit an empty part without filename
            if file.name == '':
                return CustomResponse(data="no file name", msg="fail", status=404)
            if request.FILES and allowed_file(file.name):
                filename = secure_filename(file.name)
                nexusInfo = settings.NEXUS
                params['filename'] = filename
                params["ip"] = nexusInfo["ip"]
                url = (
                    "http://{ip}/repository/xpit_temp_build/"
                    "{release}/{system}/{product}/{filename}"
                ).format(**params)
                # raise Exception(url)
                resp = requests.put(url, data=file, auth=(nexusInfo["username"], nexusInfo["password"]))
                if resp.status_code == 201:
                    res = {"success": True, "url": url, "status": resp.status_code}
                    return CustomResponse(data=res, msg="success", status=resp.status_code)
            else:
                return CustomResponse(data="file name type error", msg="fail", status=404)
        except Exception as e:
            logger.error(e)
            return CustomResponse(data=e, msg="fail", status=500)


class ApiStressArchive(APIView):

    def post(self, request):
        """
        payload:
        {
            "info": {
                BUILD_ID: "6",
                XCC: "PSI329A-1.80",
                PRODUCT: "xcc",
                IMM_USER: "USERID",
                BRANCH: "master",
                XCC-Backup: "DVI399T-8.23",
                SYSTEM: "Proton4s",
                UEFI: "PSE123O-1.60",
                NEXUSSTREAM: "xcc-master",
                RELEASE: "19c",
                IMMIP: "10.240.198.118",
                RELEASE_NAME: "19c",
                IMM_PASSWD: "SYS2009health"
            }
            "records": [records],
            "type": 0: watch_procs, 1: watch_system,
            "jobname": "PIT19C/pit_19c_entry",
            "buildno": "1"
        }
        """
        jd = json.loads(request.body.decode())
        infodata = jd["info"]
        # get the entry task.id from table task
        # entry_task = Task.query.filter_by(jobname=jd["jobname"], build_number=int(jd["buildno"])).first()

        # Check if the stress task already started, if not, create a new `StressTask` instance
        entry_taskid = Task.objects.filter(jobname=jd["jobname"], build_number=int(jd["buildno"])).order_by('-createtime')[0]
        stress_task = StressTask.objects.filter(build_number=int(infodata["BUILD_ID"]), system=infodata["SYSTEM"],
                                                release=infodata["RELEASE"], entry_taskid=entry_taskid).first()
        if not stress_task:
            stress_task = StressTask()
            stress_task.build_number = infodata["BUILD_ID"]
            stress_task.system = infodata["SYSTEM"]
            stress_task.release = infodata["RELEASE"]
            stress_task.immip = infodata["IMMIP"]
            stress_task.info = json.dumps(infodata)
            stress_task.entry_taskid = entry_taskid
            stress_task.save()
        res = {"success": True}
        return CustomResponse(data=res, msg="success")


class GetStressResult:

    def getResultURL(self, taskid):
        _info = StressTask.objects.filter(entry_taskid=int(taskid)).first()
        logger.warning(_info)
        info = json.loads(_info.info)
        if 'URL' not in info.keys():
            return None
        else:
            _url = info['URL']
            url = _url + "mem_data/result.json"
            return url

    def queryProcessGroup(self, stress_taskid=None):
        try:
            if stress_taskid is None:
                return None
            url = self.getResultURL(stress_taskid)
            if url:
                result = requests.get(url).json()
                if result:
                    lis = []
                    watchProcs = result['watchProcs']
                    for i in watchProcs:
                        if len(i['series']['rss_anon']) < 20:
                            pass
                        else:
                            first_list, last_list = i['series']['rss_anon'][10:20], i['series']['rss_anon'][-20:-10]
                            lis.append([sum(last_list) / len(last_list) - sum(first_list) / len(first_list), i['name']])
                    ret = []
                    for proces in sorted(lis, key=lambda x: x[0], reverse=True):
                        ret.append({"id": proces[1], "name": proces[1]})
                    return ret
                else:
                    logger.warning("No pid_group data in result.json")
                    return None
            else:
                return None
        except Exception as e:
            logger.warning(e)
            return None

    def queryResultData(self, stress_taskid=None):
        if stress_taskid is None:
            return None
        url = self.getResultURL(stress_taskid)
        if url:
            result = requests.get(url).json()
            if result:
                return result["watchProcs"]
            else:
                logger.warning("No pid_group data in result.json")
                return None
        else:
            return None


class ApiStressChartOptions(APIView):
    '''
    Get the pid_group
    '''

    def get(self, request):
        '''
        this id is task.id and it's also entry_id in table stress_watch_procs
        We need use task.id to find stress_task.id
        '''

        taskid = request.GET.get("id")
        if not taskid:
            # stress_taskid = StressTask.getLastTaskId()
            processNameList = []
            res = {"processNameList": processNameList}
            return CustomResponse(data=res, msg="fail")
        else:
            processNameList = GetStressResult().queryProcessGroup(taskid)
            if processNameList is None:
                processNameList = []
            res = {"processNameList": processNameList}
            return CustomResponse(data=res, msg='success')


class ApiStressChart(APIView):
    '''
    Get the watch procs data for all pid
    '''

    def get(self, request):
        res = {}
        # 0: watch-procs
        # processNamelist = request.args.getlist("processName")
        taskid = request.GET.get("id")
        processNamelist = request.GET.getlist("processName")
        stress_taskid = StressTask.objects.filter(entry_taskid=int(taskid)).first()
        processDisplay = []
        if stress_taskid.id:
            watchProcs = GetStressResult().queryResultData(taskid)
            if watchProcs:
                for processName in processNamelist:
                    for i in watchProcs:
                        if processName == i['name']:
                            processDisplay.append(i)
                            continue
        res = {"watchProcs": processDisplay}
        return CustomResponse(data=res, msg="success")


class BuildingHostInfoStages(APIView):
    authentication_classes = (JSONWebTokenAuthentication,)  # token认证
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        res = Host.objects.filter(build_number__building=1)
        logger.warning(res)
        lis = []
        for i in res:
            lis.append({"ip": i.immip, "jobname": i.build_number.jobname, 'url': i.build_number.url,
                        'release': i.build_number.release, 'user': i.build_number.username})
        ret = []
        for i in lis:
            if i not in ret:
                ret.append(i)
        return CustomResponse(data=ret, msg="success")


class TaskEmailDetailStages(APIView):
    def post(self, request):
        try:
            jd = json.loads(request.body.decode())
            build_number = jd['build_number']
            jobname = jd['jobname']
            emaildetail = jd["detail"]
            res = TaskEmailDetail.objects.filter(build_number=build_number, jobname=jobname,
                                                 emaildetail=json.dumps(emaildetail))
            if not res:
                taskmaildetail = TaskEmailDetail()
                taskmaildetail.build_number = build_number
                taskmaildetail.jobname = jobname
                taskmaildetail.emaildetail = json.dumps(emaildetail)
                taskmaildetail.taskid = \
                    Task.objects.filter(build_number=build_number, jobname=jobname).order_by('-createtime')[0]
                taskmaildetail.save()
            else:
                logger.warning("already exist")
            return CustomResponse(data="add success", msg="success")
        except Exception as e:
            logger.warning(e)
            return CustomResponse(data="no taskid", msg="fail", status=500)


class ApiTaskschedulerList(APIView, UtilMixin):
    authentication_classes = (JSONWebTokenAuthentication,)  # token认证
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        source = 0
        source = int(request.GET.get("source")) if "source" in request.GET else source
        # source = request.GET.get("source", 0, type=int)
        # source = 0
        res = []
        for task in TaskSchedule.objects.filter(source=source):
            print(task)
            taskdict = model_to_dict(task)
            taskdict["params"] = self.getParamsFromJSON(taskdict["params"], task.jobname)
            self.setExternalTaskscheduler(taskdict)
            taskdict['currentloop'] = task.count // len(taskdict["weekdays"])
            taskdict['loop'] = task.total // len(taskdict["weekdays"])
            res.append(taskdict)
        return CustomResponse(data=res, msg="success")


class ApiTaskscheduler(APIView, UtilMixin):
    authentication_classes = (JSONWebTokenAuthentication,)  # token认证
    permission_classes = (IsAuthenticated,)

    def get(self, request, sid):
        task = TaskSchedule.objects.filter(id=sid)[0]
        taskdict = model_to_dict(task)
        taskdict["params"] = self.getParamsFromJSON(taskdict["params"], task.jobname)
        self.setExternalTaskscheduler(taskdict)
        return CustomResponse(data=taskdict, msg="success")

    def delete(self, request, sid):
        username = request.session.get("username")
        task = TaskSchedule.objects.filter(id=sid)[0]
        jobname = task.jobname
        task.delete()
        event = Eventlog()
        event.events = "Deleted Task Scheduler: %s(#%s)" % (jobname, sid)
        event.result = "success"
        event.userid = User.objects.get(username=username)
        event.save()
        res = {"success": True}
        return CustomResponse(data=res, msg="success")

    def patch(self, request, sid):
        username = request.session.get("username")
        task = TaskSchedule.objects.get(id=sid)
        # properties of scheduler can be modified includes:
        # enabled, total, clock -> scheduletime, weekdays
        scheduleData = json.loads(request.body.decode())
        weekdays = util.weekdaysToInteger(w["id"] for w in scheduleData["weekdays"])
        if weekdays == 0:
            return CustomResponse(data={}, msg="fail", status=404)
        if scheduleData.get("loop", -1) < task.count // len(scheduleData["weekdays"]):
            return CustomResponse(data={}, msg="fail", status=403)
        jobname = task.jobname
        TaskSchedule.objects.filter(id=sid).update(schedule_time=util.getScheduletime(weekdays, scheduleData["clock"]),
                                                   total=scheduleData["loop"] * len(scheduleData["weekdays"]),
                                                   enabled=scheduleData.get("enabled", task.enabled), weekdays=weekdays,
                                                   updatetime=datetime.datetime.now())
        event = Eventlog()
        event.events = "Update Task Scheduler: %s(#%s)" % (jobname, sid)
        event.result = "success"
        event.userid = User.objects.get(username=username)
        event.save()
        task = TaskSchedule.objects.get(id=sid)
        taskdict = model_to_dict(task)
        taskdict["params"] = self.getParamsFromJSON(taskdict["params"], task.jobname)
        taskdict['currentloop'] = task.count // len(scheduleData["weekdays"])
        taskdict['loop'] = task.total // len(scheduleData["weekdays"])
        self.setExternalTaskscheduler(taskdict)

        return CustomResponse(data=taskdict, msg="success")
