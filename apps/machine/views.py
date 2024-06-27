import datetime
import json
import logging
import os

from django.shortcuts import render
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
from webportal import settings
from django.core.cache import cache
from machine.models import HostInfo1 as HostInfo
from machine.models import HardWare1 as Hardware
from machine.models import ConfigMessage, CommonConfigMessage
from loginAndLogout.models import Eventlog
from apps.jenkinsServer.jenkins_server.tasks import sync_jenkins_jobs, opt_job
from apps.jenkinsServer.jenkins_server.jenkins_backend import getServer
import collections
from apps.jenkinsServer.jenkins_server.jenkins_job import create_job, update_job, delete_job
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from apps.machine.machine_operation.power import system_power, XCCBackdoor
from apps.bugzila.bugzila_server.test_crontab import add_bugzila_user
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)


# Create your views here.
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


def addlog(username, action, result):
    event = Eventlog()
    event.events = f"{username} {action}"
    event.result = result
    event.userid = User.objects.get(username=username)
    event.save()


class MachineInfo(APIView):
    authentication_classes = (JSONWebTokenAuthentication,)  # token认证
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        username = request.session.get("username")
        logger.warning(username)
        ret = HostInfo.objects.all()
        lis = []
        for i in ret:
            dic = model_to_dict(i)
            try:
                hardware = Hardware.objects.get(BMCIP=dic["id"])
                dic["hardware"] = model_to_dict(hardware)
            except Hardware.DoesNotExist:
                dic['hardware'] = {"Machine": "", "CPU_Name": "", "CPU_Current_Num": "", "CPU_Max_Num": "",
                                   "DIMM_Name": "", "DIMM_Current_Num": "", "DIMM_Max_Num": "",
                                   "DIMM_Source_enough": "", "DIMM_Subcatrgory": "", "PSU_Power": "",
                                   "PSU_Current_Num": "", "PSU_Max_Num": "", "RAID_Name": "",
                                   "RAID_Current_Num": "", "HDD_Capacity": "", "HDD_Current_Num": "",
                                   "HDD_Max_Num": "",
                                   "OtherCards_Name": "", "OtherCards_Current_Num": "", "Comment": ""}
            try:
                configmess = ConfigMessage.objects.get(ConfigId=dic["id"])
                dic["config"] = model_to_dict(configmess)
            except ConfigMessage.DoesNotExist:
                dic['config'] = {"Config_name": f"config_{dic.get('Name')}_{dic.get('IMMIP')}",
                                 "Config_message": json.dumps({"test_config": {}, 'jenkins_config': {}})}
            lis.append(dic)
        res = {"success": True, "machine": lis}
        return CustomResponse(data=res, msg="get machine info success")

    def post(self, request):
        username = request.session.get("username")
        jd = json.loads(request.body.decode())
        action = jd.get('action', None)
        machine = jd.get('machine', None)
        if action == "create":
            if HostInfo.objects.filter(IMMIP=machine["IMMIP"]):
                res = {"success": False, "machine": "already exist"}
                return CustomResponse(data=res, msg="create fail", status=500)
            hostinfo = HostInfo()
            for k, v in machine.items():
                if k != "hardware":
                    setattr(hostinfo, k, v)
            hostinfo.save()
            # add hardware
            hard = machine["hardware"]
            hardwareinfo = Hardware()
            for k, v in hard.items():
                setattr(hardwareinfo, k, v)
                hardwareinfo.BMCIP = HostInfo.objects.filter(IMMIP=machine['IMMIP']).order_by("-createtime").first()
            hardwareinfo.save()
            # add config message
            conf = machine["config"]
            configMess = ConfigMessage()
            configMess.Config_name = f"config_{machine.get('Name')}_{machine.get('IMMIP')}"
            configMess.Config_message = conf['Config_message']
            configMess.ConfigId = HostInfo.objects.filter(IMMIP=machine['IMMIP']).order_by("-createtime").first()
            configMess.save()

            ret = HostInfo.objects.filter(IMMIP=machine['IMMIP']).order_by("-createtime").first()
            res = model_to_dict(ret)
            res['hardware'] = model_to_dict(Hardware.objects.get(BMCIP=res["id"]))
            res['config'] = model_to_dict(ConfigMessage.objects.get(ConfigId=res["id"]))
            if machine['Tag'] != "manual":
                if create_job(category=machine['Category'], name=machine['Name'], immip=machine['IMMIP'],
                              config=json.loads(res['config']['Config_message']), tag=machine['Tag']):
                    res = {"success": True, "machine": res}
                    addlog(username, action=f"create {machine['IMMIP']},create jenkins job success", result="success")
                    sync_jenkins_jobs()
                    return CustomResponse(data=res, msg="create success")
                else:
                    res = {"success": True, "machine": res}
                    addlog(username, action=f"create {machine['IMMIP']},create jenkins job fail", result="fail")
                    return CustomResponse(data=res, msg="create success, create jenkins job fail")
            else:
                res = {"success": True, "machine": res}
                addlog(username, action=f"create {machine['IMMIP']} success", result="success")
                return CustomResponse(data=res, msg="create success")
        elif action == "update":
            mach = HostInfo.objects.filter(id=machine['id'])
            origin_category, origin_name, orgin_immip, origin_tag = mach[0].Category, mach[0].Name, mach[0].IMMIP, mach[
                0].Tag
            hard = Hardware.objects.filter(BMCIP=machine['id'])
            conf = ConfigMessage.objects.filter(ConfigId=machine['id'])
            origin_config = json.loads(conf[0].Config_message) if conf else {}
            hardware = machine["hardware"]
            configmess = machine['config']
            now_config = json.loads(configmess['Config_message'])
            for i in HostInfo.objects.filter().exclude(id=machine["id"]).all():
                if machine['IMMIP'] == model_to_dict(i)['IMMIP']:
                    res = {"success": False, "machine": "already exist"}
                    return CustomResponse(data=res, msg="update fail")
            if mach:
                mach.update(IMMIP=machine['IMMIP'], IMMUSER=machine['IMMUSER'], IMMPASSWORD=machine['IMMPASSWORD'],
                            OSIP=machine['OSIP'], OSUSER=machine['OSUSER'], OSPASSWORD=machine['OSPASSWORD'],
                            Category=machine['Category'], Name=machine['Name'], Location=machine['Location'],
                            Host_SN=machine['Host_SN'], Comments=machine['Comments'], User=machine['User'],
                            Owner=machine['Owner'], Host_Status=machine['Host_Status'], Tag=machine['Tag'],
                            PDU=machine['PDU'], PDU_Port=machine['PDU_Port'], Sw_Config=machine['Sw_Config'],
                            Hw_Config=machine['Hw_Config'],
                            createtime=machine['createtime'], updatetime=datetime.datetime.now())
            if hard:
                hard.update(BMCIP=machine['id'], Machine=hardware["Machine"],
                            CPU_Name=hardware['CPU_Name'], CPU_Current_Num=hardware['CPU_Current_Num'],
                            CPU_Max_Num=hardware['CPU_Max_Num'], DIMM_Name=hardware['DIMM_Name'],
                            DIMM_Current_Num=hardware['DIMM_Current_Num'], DIMM_Max_Num=hardware['DIMM_Max_Num'],
                            DIMM_Source_enough=hardware['DIMM_Source_enough'],
                            DIMM_Subcatrgory=hardware['DIMM_Subcatrgory'],
                            PSU_Power=hardware['PSU_Power'], PSU_Current_Num=hardware['PSU_Current_Num'],
                            PSU_Max_Num=hardware['PSU_Max_Num'], RAID_Name=hardware['RAID_Name'],
                            RAID_Current_Num=hardware['RAID_Current_Num'], HDD_Capacity=hardware['HDD_Capacity'],
                            HDD_Current_Num=hardware['HDD_Current_Num'], HDD_Max_Num=hardware['HDD_Max_Num'],
                            OtherCards_Name=hardware['OtherCards_Name'],
                            OtherCards_Current_Num=hardware['OtherCards_Current_Num'], Comment=hardware['Comment']
                            )
            if conf:
                conf.update(ConfigId=machine['id'], Config_name=f"config_{machine.get('Name')}_{machine.get('IMMIP')}",
                            Config_message=configmess['Config_message'])
            else:
                configMess = ConfigMessage()
                configMess.Config_name = f"config_{machine.get('Name')}_{machine.get('IMMIP')}"
                configMess.Config_message = machine["config"]['Config_message']
                configMess.ConfigId = HostInfo.objects.filter(IMMIP=machine['IMMIP']).order_by("-createtime").first()
                configMess.save()
            res = model_to_dict(HostInfo.objects.filter(id=machine['id']).order_by("-updatetime").first())
            res['hardware'] = model_to_dict(Hardware.objects.get(BMCIP=res["id"]))
            if res['Tag'] != "manual":
                # if (now_config.get("jenkins_config").get("mrt") is None and res['Tag'] == "develop") or (
                #         now_config.get("jenkins_config").get("mrt") is not None and res['Tag'] != "develop"):
                #     res = {"success": False, "machine": res}
                #     return CustomResponse(data=res, msg="some issue in jenkins_config")
                if origin_tag == 'manual' or (
                        origin_config.get("jenkins_config") == {} and now_config.get("jenkins_config") != {}):
                    if create_job(category=machine['Category'], name=machine['Name'], immip=machine['IMMIP'],
                                  config=now_config, tag=machine['Tag']):
                        res = {"success": True, "machine": res}
                        addlog(username, action=f"create {machine['IMMIP']},create jenkins job success",
                               result="success")
                    sync_jenkins_jobs()
                    return CustomResponse(data=res, msg="update config success, update jenkins job success")
                else:
                    if update_job(origin_category, origin_name, orgin_immip, machine['Category'], machine['Name'],
                                  machine['IMMIP'], config=json.loads(machine['config']['Config_message']),
                                  origin_config=origin_config, tag=res['Tag'],origin_tag=origin_tag):
                        res = {"success": True, "machine": res}
                        addlog(username, action=f"update {machine['IMMIP']} success ,update jenkins job success",
                               result="success")
                        sync_jenkins_jobs()
                        return CustomResponse(data=res, msg="update config success, update jenkins job success")
                    else:
                        res = {"success": True, "machine": res}
                        addlog(username, action=f"update {machine['IMMIP']} success, update jenkins job fail",
                               result="fail")
                        return CustomResponse(data=res, msg="update config success, update jenkins job fail")
            else:
                if origin_tag != 'manual':
                    if delete_job(origin_category, origin_name, orgin_immip, origin_config, origin_tag):
                        res = {"success": True}
                        addlog(username, action=f"delete machine_id:{machine['id']}", result="success")
                        sync_jenkins_jobs()
                res = {"success": True, "machine": res}
                addlog(username, action=f"update {machine['IMMIP']} success",
                       result="success")
                return CustomResponse(data=res, msg="update success")
        elif action == "delete":
            mach = HostInfo.objects.filter(id=machine['id'])
            tag = mach[0].Tag
            origin_category, origin_name, orgin_immip = mach[0].Category, mach[0].Name, mach[0].IMMIP
            hardware = Hardware.objects.filter(BMCIP=machine['id'])
            conf = ConfigMessage.objects.filter(ConfigId=machine['id'])
            if conf:
                conf_mess = json.loads(conf[0].Config_message)
                conf.delete()
            else:
                conf_mess = {}
            if hardware: hardware.delete()
            mach = HostInfo.objects.filter(id=machine['id'])
            if mach:
                mach.delete()
            else:
                res = {"success": False}
                return CustomResponse(data=res, msg="delete fail,no id")
            if tag != "manual":
                if delete_job(origin_category, origin_name, orgin_immip, conf_mess, tag):
                    res = {"success": True}
                    addlog(username, action=f"delete machine_id:{machine['id']}", result="success")
                    sync_jenkins_jobs()
                    return CustomResponse(data=res, msg="delete success, delete jenkins job success")
                else:
                    res = {"success": True}
                    addlog(username, action=f"delete machine_id:{machine['id']} success ,delete jenkins job fail",
                           result="fail")
                    return CustomResponse(data=res, msg="delete success , delete jenkins job fail")
            else:
                res = {"success": True}
                addlog(username, action=f"delete machine_id:{machine['id']}", result="success")
                return CustomResponse(data=res, msg="delete success")


class AllConfigMess(APIView):
    authentication_classes = (JSONWebTokenAuthentication,)  # token认证
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        configmess_list = ConfigMessage.objects.all()
        config_dic = {"host": {}, 'config': {}, "common": {}}
        for configmess in configmess_list:
            hostinfo = model_to_dict(configmess.ConfigId)
            config_dic["host"][hostinfo['Category']], config_dic['config'][hostinfo['Category']] = {}, []
        for configmess in configmess_list:
            hostinfo = model_to_dict(configmess.ConfigId)
            configinfo = model_to_dict(configmess)
            hostinner = {}
            if hostinfo.get('PDU') is not None and hostinfo.get('PDU_Port') is not None:
                hostinner['PDU'] = {"name": hostinfo.get('PDU'), "ports": hostinfo.get('PDU_Port').split(' ')}
            else:
                hostinner['PDU'] = {"name": hostinfo.get('PDU'), "ports": ['']}
            hostinner['codename'] = hostinfo.get('Name')
            hostinner['description'] = hostinfo.get('Comments')
            hostinner['immip'] = hostinfo.get('IMMIP')
            hostinner['immpasswd'] = hostinfo.get('IMMPASSWORD')
            hostinner['immuser'] = hostinfo.get('IMMUSER')
            hostinner['osip'] = hostinfo.get('OSIP')
            hostinner['ospasswd'] = hostinfo.get('OSPASSWORD')
            hostinner['osuser'] = hostinfo.get('OSUSER')
            hostinner['build_config'] = configinfo['Config_name']
            hostinner['releases'] = hostinfo.get('Category').lower().split(' ')
            hostinner['system'] = hostinfo.get('Name')
            # if not config_dic.get(hostinfo['Category']):
            config_dic["host"][hostinfo['Category']][hostinfo['IMMIP'].replace('.', "_")] = hostinner
            config_dic['config'][hostinfo['Category']].append({configinfo['Config_name']: configinfo['Config_message']})
        for k, v in config_dic['host'].items():
            config_dic['host'][k] = json.dumps(v)
        commonlist = CommonConfigMessage.objects.all()
        for common in commonlist:
            config_dic['common'][common.CommonConfigName] = common.CommonConfig_message
        res = {"success": True, "allconfig": config_dic}
        return CustomResponse(data=res, msg="get all config info success")


class CommonConfigMess(APIView):
    authentication_classes = (JSONWebTokenAuthentication,)  # token认证
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        ret = []
        res = CommonConfigMessage.objects.all()
        [ret.append(model_to_dict(commonconfig)) for commonconfig in res]
        res = {"success": True, "allconfig": ret}
        return CustomResponse(data=res, msg="get common config info success")

    def post(self, request):
        username = request.session.get("username")
        jd = json.loads(request.body.decode())
        commonid = jd.get('id', None)
        action = jd.get('action', None)
        if action == "update":
            message = jd.get('CommonConfig_message')
            CommonConfigMessage.objects.filter(id=commonid).update(CommonConfig_message=message)
            res = {"success": True}
            addlog(username,
                   action=f"update commonconfig id:{commonid} configmessage_name: {CommonConfigMessage.objects.get(id=commonid).CommonConfigName}",
                   result="success")
            # update bugzila user
            add_bugzila_user()
            return CustomResponse(data=res, msg="update common config info success")
        elif action == "delete":
            name = CommonConfigMessage.objects.get(id=commonid).CommonConfigName
            CommonConfigMessage.objects.filter(id=commonid).delete()
            res = {"success": True}
            addlog(username, action=f"delete commonconfig id:{commonid} configmessage_name: {name}", result="success")
            return CustomResponse(data=res, msg="delete common config info success")
        elif action == "create":
            message = jd.get('CommonConfig_message')
            name = jd.get('CommonConfigName')
            commonConfigMessage = CommonConfigMessage()
            commonConfigMessage.CommonConfigName = name
            commonConfigMessage.CommonConfig_message = message
            commonConfigMessage.save()
            res = {"success": True}
            addlog(username, action=f"create commonid:{commonid} commonconfig name: {name}", result="success")
            return CustomResponse(data=res, msg="create common config info success")


class CommonCategoryRelease(APIView):
    authentication_classes = (JSONWebTokenAuthentication,)  # token认证
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        ret = []
        res = CommonConfigMessage.objects.get(CommonConfigName="releases")
        # [ret.append(model_to_dict(commonconfig)) for commonconfig in res]
        for k, v in json.loads(res.CommonConfig_message).items():
            ret.append(k)
        res = {"success": True, "cagegory": ret}
        return CustomResponse(data=res, msg="get common config info success")


class PowerAction(APIView):
    authentication_classes = (JSONWebTokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            powerStatus = cache.get('powerStatus')
        except Exception as e:
            logger.error(e)
            powerStatus = {}
        return CustomResponse(data=powerStatus, msg="get powerstatus success")

    def post(self, request):
        jd = json.loads(request.body.decode())
        action = jd.get('action', None)
        immip = jd.get("immip", None)
        host = HostInfo.objects.filter(IMMIP=immip)[0]
        username, password = host.IMMUSER, host.IMMPASSWORD
        res = {"success": True}
        if username == "" or username is None or password == "" or password is None:
            res['success'] = False
            return CustomResponse(data=res, msg="username or password wrong", status=400)
        if system_power(immip, username, password, action):
            return CustomResponse(data=res, msg=f"power {action} success")
        else:
            res['success'] = False
            return CustomResponse(data=res, msg="power on fail", status=400)


class OpenBackDoorAction(APIView):
    authentication_classes = (JSONWebTokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_open_backdoor_config(self, ip):
        host = HostInfo.objects.filter(IMMIP=ip)
        hostid = host[0].id if host else ""
        config = ConfigMessage.objects.filter(ConfigId=int(hostid))
        config_mess = json.loads(config[0].Config_message) if config else {}
        test_config = config_mess.get("test_config", {})
        openbackdoor_config = test_config.get("open_backdoor", 'debug_sign_4k384')
        return openbackdoor_config

    def post(self, request):
        jd = json.loads(request.body.decode())
        immip = jd.get("immip", None)
        host = HostInfo.objects.filter(IMMIP=immip)[0]
        username, password = host.IMMUSER, host.IMMPASSWORD
        res = {"success": True}
        if os.system(f'ping -c 1 {immip}') == 0:
            print('IP available')
        else:
            res['success'] = False
            return CustomResponse(data=res, msg=f"current ip {immip} is unavailable", status=400)
        if username == "" or username is None or password == "" or password is None:
            res['success'] = False
            return CustomResponse(data=res, msg="username or password wrong", status=400)
        xccbackdoor = XCCBackdoor(immip, username, password)
        if xccbackdoor.openbackdoor(backdoorconfig=self.get_open_backdoor_config(immip)):
            return CustomResponse(data=res, msg=f"open backdoor success")
        else:
            res['success'] = False
            return CustomResponse(data=res, msg="open backdoor fail", status=400)
