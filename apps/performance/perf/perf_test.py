# -*- coding: utf-8 -*-
"""
@Time ： 3/10/23 4:02 PM
@Auth ： gujie5
"""
import traceback
from datetime import datetime, timedelta
from django.db.models import Q
import django
from django.db import connection
import os
import json

from django.forms import model_to_dict
from numpy import *

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webportal.settings')
django.setup()
from performance.models import Cases, HostHWInfo, HostSWInfo, Performance

pro_path = os.path.abspath(os.path.dirname(__file__))


def getResult_1(l):
    res = []
    keys = set([item[i]['perf_category'] for item in l for i in range(0, len(item))])
    for ip in keys:
        tmp = []
        for ite in l:
            for i in range(0, len(ite)):
                if ip == ite[i]['perf_category']:
                    tmp.append(ite[i])
            res.append(tmp)
    res_dict = dict()
    for i in res:
        res_dict[i[0]["perf_category"]] = i
    return res_dict


def archive_cases_info(json_info):
    result = json_info
    database_case_list = []
    cases = Cases.objects.all()
    for c in cases:
        database_case_list.append(c.case_name)
    print(database_case_list)
    data = list()
    for val in range(len(result["PERFORMANCE"])):
        for k, v in result["PERFORMANCE"][val].items():
            case_name = v["case_name"].strip(f"_{val + 1}")
            if case_name not in database_case_list:
                data.append(case_name)
    print(data)
    if data:
        for i in data: Cases.objects.create(case_name=i)


def archive_hw_info(json_info):
    result = json_info
    data = {"job_id": result['JOB_ID']}
    hw_info = result['HW_INFO']
    cpu_info, mem_info, pcie_info, hdd_info = [], [], [], []
    for k, v in hw_info.items():
        if k == "CPU":
            if v != "NA":
                for kk, vv in v.items():
                    if kk == "CPU_NUMBERS":
                        data["cpu_num"] = vv
                    else:
                        cpu_info.append(result["HW_INFO"]["CPU"][kk]["Processor Vision"])
            else:
                cpu_info.append("NA")
            data["cpu_info"] = f"{cpu_info}"
        elif k == "MEM":
            if v != "NA":
                sum = 0
                for kk, vv in v.items():
                    mem_info.append(kk)
                    sum += int(vv)
                data["mem_num"] = sum
            else:
                mem_info.append("NA")
                data["mem_num"] = 0
            data["mem_info"] = f"{mem_info}"
        elif k == "PCIE":
            if v != "NA":
                sum = 0
                for kk, vv in v.items():
                    pcie_info.append(kk)
                    sum += int(vv)
                data["pcie_num"] = sum
            else:
                pcie_info.append("NA")
                data["pcie_num"] = 0
            data["pcie_info"] = f"{pcie_info}"
        elif k == "HDD":
            if v != "NA":
                sum = 0
                for kk, vv in v.items():
                    hdd_info.append(kk)
                    sum += int(vv)
                data["hdd_num"] = sum
            else:
                hdd_info.append("NA")
                data["hdd_num"] = 0
            data["hdd_info"] = f"{hdd_info}"
        elif k == "IMMIP":
            data["bmc_ip"] = v
        elif k == "BOARD":
            data["mb_phase"] = v["VERSION"]
        elif k == "MACHINE_TYPE":
            data["machine_type"] = v
        elif k == "SYSTEM":
            data["platform_name"] = v
    data["bmc_mac"] = result["SW_INFO"]["bmc_mac"]["current"]
    data["smbios"] = result["SW_INFO"]["SMBIOS"]["current"]
    HostHWInfo.objects.create(**data)


def archive_sw_info(json_info):
    result = json_info
    data = {"job_id": result['JOB_ID'], "release": result["HW_INFO"]["RELEASE"]}
    hw_info = result['SW_INFO']
    lis = ["XCC", "UEFI", "LXPM", "FPGA", "PFR EC", "ME Firmware Version"]
    for k, v in hw_info.items():
        if k in lis:
            if k == "ME Firmware Version":
                data["before_me"] = v["before"]
                data["current_me"] = v["current"]
            elif k == "PFR EC":
                data["before_pfr"] = v["before"]
                data["current_pfr"] = v["current"]
            else:
                data[f"before_{str.lower(k)}"] = v["before"]
                data[f"current_{str.lower(k)}"] = v["current"]
    print(data)
    HostSWInfo.objects.create(**data)


def achive_performance_info(json_info):
    result = json_info
    # data["job_id"] = result['JOB_ID']
    time_list = ["web_server", "ipmi_server",
                 "cli_server", "redfish_server",
                 "boot_to_f1", "boot_to_os",
                 "flash_xcc", "flash_uefi"]
    hw_info = HostHWInfo.objects.all().order_by("-id")
    sw_info = HostSWInfo.objects.all().order_by("-id")
    latest_hw_info = hw_info[0].id
    latest_sw_info = sw_info[0].id
    inset_mess = []
    try:
        for performance in result["PERFORMANCE"]:
            # print(performance)
            performance_sort = result["PERFORMANCE"].index(performance)
            for casename, case in performance.items():
                if performance_sort < 9:
                    sor = -2
                elif 9 <= performance_sort < 99:
                    sor = -3
                elif performance_sort >= 99:
                    sor = -4
                li = []
                job_id = result["JOB_ID"]
                date = case["date"]
                for key, value in case.items():
                    if type(value) is dict:
                        for time in time_list:
                            if time in value:
                                li.append({"ffdc_real": key, "server": time, "performance": value[time]})
                if li != []:
                    ffdc_or_real_lis, server = [], []
                    for i in li:
                        ffdc_or_real_lis.append(i["ffdc_real"])
                    if len(set(ffdc_or_real_lis)) == 2:
                        for i in li:
                            server.append(i["server"])
                        list(set(server))
                        lis, new_lis = [], []
                        for j in server:
                            ffdc_real_list = []
                            for i in li:
                                if j == i["server"]:
                                    ffdc_real_list.append(i)
                            lis.append(ffdc_real_list)
                        for cas in lis:
                            if cas not in new_lis:
                                new_lis.append(cas)
                        for i in new_lis:
                            # print(job_id,date,case["case_name"],"=======",i)
                            if len(i) == 2:
                                if i[0]["ffdc_real"] == "ffdc":
                                    # print(job_id, date, case["case_name"], "=======", i)
                                    two_perf = Performance(job_id=job_id, date=date, perf_category=i[0]["server"],
                                                           ffdc_times=i[0]["performance"],
                                                           real_times=i[1]["performance"],
                                                           host_hw_info_id=HostHWInfo.objects.all().order_by("-id")[0],
                                                           host_sw_info_id=HostSWInfo.objects.all().order_by("-id")[0],
                                                           case_name_id=Cases.objects.get(case_name=
                                                                                          case["case_name"][0: sor]))
                                    inset_mess.append(two_perf)
                                elif i[0]["ffdc_real"] == "real_time":
                                    two_perf = Performance(job_id=job_id, date=date, perf_category=i[0]["server"],
                                                           ffdc_times=i[1]["performance"],
                                                           real_times=i[0]["performance"],
                                                           host_hw_info_id=HostHWInfo.objects.all().order_by("-id")[0],
                                                           host_sw_info_id=HostSWInfo.objects.all().order_by("-id")[0],
                                                           case_name_id=Cases.objects.get(case_name=
                                                                                          case["case_name"][0: sor]))
                                    inset_mess.append(two_perf)
                            elif len(i) == 1:
                                if i[0]["ffdc_real"] == "real_time":
                                    one_perf = Performance(job_id=job_id, date=date, perf_category=i[0]["server"],
                                                           real_times=i[0]["performance"],
                                                           host_hw_info_id=HostHWInfo.objects.all().order_by("-id")[0],
                                                           host_sw_info_id=HostSWInfo.objects.all().order_by("-id")[0],
                                                           case_name_id=Cases.objects.get(case_name=
                                                                                          case["case_name"][0: sor]))
                                else:
                                    one_perf = Performance(job_id=job_id, date=date, perf_category=i[0]["server"],
                                                           ffdc_times=i[0]["performance"],
                                                           host_hw_info_id=HostHWInfo.objects.all().order_by("-id")[0],
                                                           host_sw_info_id=HostSWInfo.objects.all().order_by("-id")[0],
                                                           case_name_id=Cases.objects.get(case_name=
                                                                                          case["case_name"][0: sor]))
                                inset_mess.append(one_perf)
                    elif len(set(ffdc_or_real_lis)) == 1:
                        for i in li:
                            print(case["case_name"][0: sor], i)
                            if i["ffdc_real"] == "ffdc":
                                ffdc_perf = Performance(job_id=job_id, date=date, perf_category=i["server"],
                                                        ffdc_times=i["performance"],
                                                        host_hw_info_id=HostHWInfo.objects.all().order_by("-id")[0],
                                                        host_sw_info_id=HostSWInfo.objects.all().order_by("-id")[0],
                                                        case_name_id=Cases.objects.get(case_name=
                                                                                       case["case_name"][0: sor]))
                                inset_mess.append(ffdc_perf)
                            else:
                                real_perf = Performance(job_id=job_id, date=date, perf_category=i["server"],
                                                        real_times=i["performance"],
                                                        host_hw_info_id=HostHWInfo.objects.all().order_by("-id")[0],
                                                        host_sw_info_id=HostSWInfo.objects.all().order_by("-id")[0],
                                                        case_name_id=Cases.objects.get(case_name=
                                                                                       case["case_name"][0: sor]))
                                inset_mess.append(real_perf)
        Performance.objects.bulk_create(inset_mess)
    except Exception as e:
        print(e)
        print("\n" + traceback.format_exc())
    # print(casename,"==========",ffdc_real_list)


# with open("/home/test/PycharmProjects/pythonProject/wp_pro/info.json", "r", encoding="utf-8") as f:
#     content = json.load(f)
#     archive_cases_info(content)
#     archive_hw_info(content)
#     archive_sw_info(content)
#     res = achive_performance_info(content)
#     print(res)


class Query:

    def avg_case_realtime(self, casename):
        case = Cases.objects.filter('case_name' == casename).first()
        # print(case.performance)
        time_lis = []
        for i in range(len(case.performance)):
            real_time = case.performance[i].real_times
            if real_time is not None:
                time_lis.append(real_time)
        print(mean(time_lis))

    def avg_case_ffdctime(self, casename):
        case = Cases.objects.filter('case_name' == casename).first()
        # print(case.performance)
        time_lis = []
        for i in range(len(case.performance)):
            ffdc = case.performance[i].ffdc_times
            if ffdc is not None:
                time_lis.append(ffdc)
        print(mean(time_lis))

    def get_hw_info(self, id):
        hw = HostHWInfo.objects.all()
        for h in hw:
            print(h.job_id, h.mem_info, h.performance[2].real_times)

    def get_sw_info(self):
        sw = HostSWInfo.objects.all()
        for s in sw:
            print(s.job_id, s.current_xcc, s.performance[2].ffdc_times)

    def get_case_info(self):
        case = Cases.objects.all()
        result = list()
        for c in case:
            dic = dict()
            dic["caseId"] = c.id
            dic['casename'] = c.case_name
            result.append(dic)

        return {'code': '0000', "data": {"results": result},"msg": "success"}

    def query_case(self, casename):
        case = Cases.objects.all()
        for c in case:
            if c.case_name == casename:
                return c.id

    def query_case_by_id(self, caseid):
        case = Cases.objects.all()
        for c in case:
            if c.id == caseid:
                return c.case_name

    def get_platform(self):
        hw = HostHWInfo.objects.values('platform_name').distinct().all()
        print(hw)
        lis, result = [], []
        for h in hw:
            lis.append(h['platform_name'])
        for i in range(len(lis)):
            dic = dict()
            dic["platformId"] = i + 1
            dic["platform"] = lis[i]
            result.append(dic)

        return {'code': '0000', "data": {"results": result},"msg": "success"}

    def get_bmc_mac(self):
        hw = HostHWInfo.objects.values('bmc_mac').distinct().all()
        lis, result = [], []
        for h in hw:
            if h['bmc_mac'] != "na":
                lis.append(h['bmc_mac'])
        for i in range(len(lis)):
            dic = dict()
            dic["macId"] = i + 1
            dic["mac"] = lis[i]
            result.append(dic)

        return {'code': '0000', "data": {"results": result},"msg": "success"}

    def search(self, start_date, end_date, case_name_id, platform, mac):
        time_now = datetime.now()
        if case_name_id is not None and platform is not None and mac is not None:
            if start_date is None and end_date is None:
                perf = Performance.objects.filter(date__gte=time_now - timedelta(days=90)).filter(
                    host_hw_info_id__platform_name=platform).filter(host_hw_info_id__bmc_mac=mac).filter(
                    case_name_id__case_name=case_name_id).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            elif start_date is None and end_date is not None:
                perf = Performance.objects.filter(date__lte=end_date).filter(
                    host_hw_info_id__platform_name=platform).filter(host_hw_info_id__bmc_mac=mac).filter(
                    case_name_id__case_name=case_name_id).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            elif start_date is not None and end_date is None:
                perf = Performance.objects.filter(date__gte=start_date).filter(
                    host_hw_info_id__platform_name=platform).filter(host_hw_info_id__bmc_mac=mac).filter(
                    case_name_id__case_name=case_name_id).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            else:
                perf = Performance.objects.filter(date__range=(start_date, end_date)).filter(
                    host_hw_info_id__platform_name=platform).filter(host_hw_info_id__bmc_mac=mac).filter(
                    case_name_id__case_name=case_name_id).select_related("host_hw_info_id").select_related(
                    "host_sw_info_id").select_related("case_name_id")
        elif case_name_id is None and platform is not None and mac is not None:
            if start_date is None and end_date is None:
                perf = Performance.objects.filter(date__gte=time_now - timedelta(days=90)).filter(
                    host_hw_info_id__platform_name=platform).filter(host_hw_info_id__bmc_mac=mac).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            elif start_date is None and end_date is not None:
                perf = Performance.objects.filter(date__lte=end_date).filter(
                    host_hw_info_id__platform_name=platform).filter(host_hw_info_id__bmc_mac=mac).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            elif start_date is not None and end_date is None:
                perf = Performance.objects.filter(date__gte=start_date).filter(
                    host_hw_info_id__platform_name=platform).filter(host_hw_info_id__bmc_mac=mac).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            else:
                perf = Performance.objects.filter(date__range=(start_date, end_date)).filter(
                    host_hw_info_id__platform_name=platform).filter(host_hw_info_id__bmc_mac=mac).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
        elif case_name_id is not None and platform is None and mac is not None:
            if start_date is None and end_date is None:
                perf = Performance.objects.filter(date__gte=time_now - timedelta(days=90)).filter(
                    host_hw_info_id__bmc_mac=mac).filter(case_name_id__case_name=case_name_id).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            elif start_date is None and end_date is not None:
                perf = Performance.objects.filter(date__lte=end_date).filter(host_hw_info_id__bmc_mac=mac).filter(
                    case_name_id__case_name=case_name_id).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            elif start_date is not None and end_date is None:
                perf = Performance.objects.filter(date__gte=start_date).filter(host_hw_info_id__bmc_mac=mac).filter(
                    case_name_id__case_name=case_name_id).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            else:
                perf = Performance.objects.filter(date__range=(start_date, end_date)).filter(
                    host_hw_info_id__bmc_mac=mac).filter(case_name_id__case_name=case_name_id).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
        elif case_name_id is not None and platform is not None and mac is None:
            if start_date is None and end_date is None:
                perf = Performance.objects.filter(date__gte=time_now - timedelta(days=90)).filter(
                    host_hw_info_id__platform_name=platform).filter(
                    case_name_id__case_name=case_name_id).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            elif start_date is None and end_date is not None:
                perf = Performance.objects.filter(date__lte=end_date).filter(
                    host_hw_info_id__platform_name=platform).filter(
                    case_name_id__case_name=case_name_id).select_related("host_hw_info_id").select_related(
                    "host_sw_info_id").select_related("case_name_id")
            elif start_date is not None and end_date is None:
                perf = Performance.objects.filter(date__gte=start_date).filter(
                    host_hw_info_id__platform_name=platform).filter(
                    case_name_id__case_name=case_name_id).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            else:
                perf = Performance.objects.filter(date__range=(start_date, end_date)).filter(
                    host_hw_info_id__platform_name=platform).filter(
                    case_name_id__case_name=case_name_id).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
                print(perf)
        elif case_name_id is None and platform is None and mac is not None:
            if start_date is None and end_date is None:
                perf = Performance.objects.filter(date__gte=time_now - timedelta(days=90)).filter(
                    host_hw_info_id__bmc_mac=mac).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            elif start_date is None and end_date is not None:
                perf = Performance.objects.filter(date__lte=end_date).filter(
                    host_hw_info_id__bmc_mac=mac).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            elif start_date is not None and end_date is None:
                perf = Performance.objects.filter(date__gte=start_date).filter(
                    host_hw_info_id__bmc_mac=mac).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            else:
                perf = Performance.objects.filter(date__range=(start_date, end_date)).filter(
                    host_hw_info_id__bmc_mac=mac).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
        elif case_name_id is None and platform is not None and mac is None:
            if start_date is None and end_date is None:
                perf = Performance.objects.filter(date__gte=time_now - timedelta(days=90)).filter(
                    host_hw_info_id__platform_name=platform).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            elif start_date is None and end_date is not None:
                perf = Performance.objects.filter(date__lte=end_date).filter(
                    host_hw_info_id__platform_name=platform).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            elif start_date is not None and end_date is None:
                perf = Performance.objects.filter(date__gte=start_date).filter(
                    host_hw_info_id__platform_name=platform).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            else:
                perf = Performance.objects.filter(date__range=(start_date, end_date)).filter(
                    host_hw_info_id__platform_name=platform).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
        elif case_name_id is not None and platform is None and mac is None:
            if start_date is None and end_date is None:
                perf = Performance.objects.filter(date__gte=time_now - timedelta(days=90)).filter(
                    case_name_id__case_name=case_name_id).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            elif start_date is None and end_date is not None:
                perf = Performance.objects.filter(date__lte=end_date).filter(
                    case_name_id__case_name=case_name_id).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            elif start_date is not None and end_date is None:
                perf = Performance.objects.filter(date__gte=start_date).filter(
                    case_name_id__case_name=case_name_id).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            else:
                perf = Performance.objects.filter(date__range=(start_date, end_date)).filter(
                    case_name_id__case_name=case_name_id).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
        else:
            if start_date is None and end_date is None:
                perf = Performance.objects.filter(date__gte=time_now - timedelta(days=90)).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            elif start_date is None and end_date is not None:
                perf = Performance.objects.filter(date__lte=end_date).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            elif start_date is not None and end_date is None:
                perf = Performance.objects.filter(date__gte=start_date).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
            else:
                perf = Performance.objects.filter(date__range=(start_date, end_date)).select_related(
                    "host_hw_info_id").select_related("host_sw_info_id").select_related("case_name_id")
        lis = []
        print(perf)
        if perf != []:
            for p in perf:
                # times = performance.date
                dic = {
                    "perf_category": p.perf_category,
                    "job_id": p.job_id,
                    "date": p.date.strftime("%Y-%m-%d %H:%M:%S"),
                    "ffdc_times": p.ffdc_times,
                    "real_times": p.real_times,
                    "hw": {
                        "machine_type": p.host_hw_info_id.machine_type,
                        "bmc_ip": p.host_hw_info_id.bmc_ip,
                        "cpu_num": p.host_hw_info_id.cpu_num,
                        "cpu_info": p.host_hw_info_id.cpu_info,
                        "mem_num": p.host_hw_info_id.mem_num,
                        "mem_info": p.host_hw_info_id.mem_info,
                        "pcie_num": p.host_hw_info_id.pcie_num,
                        "pcie_info": p.host_hw_info_id.pcie_info,
                        "hdd_num": p.host_hw_info_id.hdd_num,
                        "hdd_info": p.host_hw_info_id.hdd_info,
                        "smbios": p.host_hw_info_id.smbios,
                        "mb_phase": p.host_hw_info_id.mb_phase
                    },
                    "sw": {
                        "release": p.host_sw_info_id.release,
                        "before_xcc": p.host_sw_info_id.before_xcc,
                        "current_xcc": p.host_sw_info_id.current_xcc,
                        "before_uefi": p.host_sw_info_id.before_uefi,
                        "current_uefi": p.host_sw_info_id.current_uefi,
                        "before_lxpm": p.host_sw_info_id.before_lxpm,
                        "current_lxpm": p.host_sw_info_id.current_lxpm,
                        "before_pfr": p.host_sw_info_id.before_pfr,
                        "current_pfr": p.host_sw_info_id.current_pfr,
                        "before_fpga": p.host_sw_info_id.before_fpga,
                        "current_fpga": p.host_sw_info_id.current_fpga,
                        "before_me": p.host_sw_info_id.before_me,
                        "current_me": p.host_sw_info_id.current_me
                    }
                }
                lis.append(dic)

        else:
            return {'code': '9999', "data": {"results": "no response"}}
        # per = list(set(perf_lis))
        # result = sorted(lis, key=lambda x: x['perf_category'])
        return {'code': '0000', "data": {"results": getResult_1([lis])},"msg": "success"}

    def get_case_mac_by_caseid(self, platform):
        try:
            perf = Performance.objects.filter(host_hw_info_id__platform_name=platform).filter(
                ~Q(host_hw_info_id__bmc_mac="na")).filter(~Q(host_hw_info_id__bmc_mac="NA")).select_related(
                "host_hw_info_id").select_related("case_name_id")
            mac_list, case_list = [], []
            for p in perf:
                if p.host_hw_info_id.bmc_mac not in mac_list:
                    mac_list.append(p.host_hw_info_id.bmc_mac)
                if p.case_name_id.case_name not in case_list:
                    case_list.append(p.case_name_id.case_name)
            print("Success")
            return {'code': '0000', "data": {"case": case_list, "mac": mac_list},"msg": "success"}
        except Exception as e:
            print(e)
            print("\n" + traceback.format_exc())
            return {}
