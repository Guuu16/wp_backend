import json
import time

import datetime
from collections import Counter
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.forms import model_to_dict
from django.views.decorators.cache import never_cache, cache_page
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from apps.bugzila.bugzila_server.bugzilawebservice import BugzillaWebService
from webportal import settings
# Create your views here.
from cache_helper import get_cache_or_exc_func
from django.core.cache import cache

bugzila = BugzillaWebService(url_base="https://bz.labs.company.com", token="3546-t2iKyULbjn")

res = {
    "msg": "success",
    "data": ""
}


def get_week_list(now):
    lis = []
    for i in range(10, -2, -1):
        lis.append([((now - datetime.timedelta(days=now.isoweekday() + 6)) - datetime.timedelta(days=i * 7)),
                    ((now - datetime.timedelta(days=now.isoweekday() + 0)) - datetime.timedelta(days=i * 7))])
    return lis


def index(request):
    return render(request, "bug/index.html")


def Bug_user(request):
    from bugzila.models import User
    if request.method == "POST":
        if request.body.decode() == '':
            res['data'] = "body is Null!"
            res['msg'] = 'fail'
            return JsonResponse(res, safe=False, status=500)
        else:
            res['msg'] = 'success'
            body = eval(request.body)
            if body["type"] == "delete":
                for i in body["email"]:
                    try:
                        User.objects.get(user=i).delete()
                        print(f"Delete {i} success")
                    except User.DoesNotExist:
                        res['data'] = F'{i} not exist'
                        res['msg'] = 'fail'
                        return JsonResponse(res, safe=False, status=500)
                    res['data'] = "delete user success"
            elif body['type'] == 'add':
                for i in body["email"]:
                    try:
                        User.objects.get(user=i)
                        print(f"No need to add {i}")
                    except User.DoesNotExist:
                        user = User()
                        user.user = i
                        user.auto_or_manual = body["auto_or_manual"]
                        user.save()
                res['data'] = "add Bug user success"
            elif body['type'] == 'update':
                for i in body["email"]:
                    User.objects.filter(user=i).update(user=body['update'])
                    res['data'] = "update Bug user success"
            return JsonResponse(res, safe=False)
    else:
        data = User.objects.all()
        res['data'] = list()
        for user in data:
            temp = model_to_dict(user)
            res['data'].append(temp)
        return JsonResponse(res, safe=False)


def get_bug(request, bugId):
    result = bugzila.Get_Bug(bugId)
    res["data"] = result[1]
    if result[0] is False:
        res['msg'] = 'fail'
        return HttpResponse(res, status=500, safe=False)
    else:
        return JsonResponse(res, status=200, safe=False)


def get_total_bug(request):
    if request.method == "POST":
        if request.body.decode() == '':
            res['status'] = "500"
            res['data'] = "body is Null!"
            return JsonResponse(res)
        else:
            print(request)
            body = request.POST
            auto_or_manual = body["auto_or_manual"]
            start_date = datetime.datetime.strptime("2022-04-01", '%Y-%m-%d')
            start_date = datetime.datetime.strptime(body["creation_time"],
                                                    '%Y-%m-%d') if "creation_time" in body else start_date
            end_date = datetime.datetime.now() + datetime.timedelta(hours=23, minutes=59, seconds=59)
            end_date = datetime.datetime.strptime(body["end_time"], '%Y-%m-%d') + datetime.timedelta(hours=23,
                                                                                                     minutes=59,
                                                                                                     seconds=59) if "end_time" in body else end_date
            result = cache.get(auto_or_manual)
            d_list = [item for item in result[1]["bugs"] if
                      start_date < datetime.datetime.strptime(item["creation_time"], '%Y-%m-%dT%H:%M:%SZ') < end_date]
            result[1]["bugs"] = d_list
            result[1]["bug_total"] = {}
            result[1]["bug_total"]["total_bug"] = len(result[1]["bugs"])
            bug_lis = []
            [bug_lis.append(bug["status"]) for bug in result[1]["bugs"]]
            result[1]["bug_total"].update(dict(Counter(bug_lis)))
            res["data"] = result[1]
            if result[0] is False:
                res["status"] = "500"
                res['msg'] = 'fail'
                return JsonResponse(res, status=500, safe=False)
            else:
                res["status"] = "200"
                return JsonResponse(res, status=200, safe=False)


def get_bug_classfied(request):
    item = settings.SEARCH_ITEM
    start = request.GET.get('start')
    end = request.GET.get("end")
    start_date = datetime.datetime.strptime("2022-04-01", '%Y-%m-%d')
    start_date = datetime.datetime.strptime(start, '%Y-%m-%d') if start is not None else start_date
    end_date = datetime.datetime.now() + datetime.timedelta(hours=23, minutes=59, seconds=59)
    end_date = datetime.datetime.strptime(end, '%Y-%m-%d') + datetime.timedelta(hours=23, minutes=59,
                                                                                seconds=59) if end is not None else end_date
    ret = {}
    for i in item:
        result = cache.get(i)
        d_list = [item for item in result[1]["bugs"] if
                  start_date < datetime.datetime.strptime(item["creation_time"], '%Y-%m-%dT%H:%M:%SZ') < end_date]
        result[1]["bugs"] = d_list
        result[1]["bug_total"] = {}
        result[1]["bug_total"]["total_bug"] = len(result[1]["bugs"])
        bug_lis = [bug["status"] for bug in result[1]["bugs"]]
        detail = []
        for message in result[1]['bugs']:
            detail.append(
                {"Id": message['id'], "Creator": message['creator'], 'Release': message['version'],
                 'Product': message['product'],
                 'Component': message['component'], 'Assignee': message['assigned_to'],
                 'Status': message['status'], 'Resolution': message['resolution'],
                 'Summary': message['summary'], 'Create_time': message['creation_time']})
        result[1]["bug_total"].update(dict(Counter(bug_lis)))
        lis = []
        for k, v in dict(Counter(bug_lis)).items():
            lis.append({"name": k, "value": v, "detail": []})
        j = 0
        while j < len(detail):
            for s in range(len(lis)):
                lis[s]['detail'].append(detail[j]) if lis[s]['name'] == detail[j]['Status'] else lis[s]['detail']
            j += 1
        else:
            pass
        ret[i] = lis
    res['data'] = {"classified": ret}
    # res["data"] = result[1]
    # print(result[1])
    return JsonResponse(res)


def get_bug_history(request, id):
    result = bugzila.Bug_History(bug_id=str(id))
    if result[0] is False:
        if "not authorized to access" in result[1]:
            res['data'] = f"You are not authorized to access bug {id}"
            return JsonResponse(res, status=500, safe=False)
        else:
            res['data'] = "some error ,please check url"
            res['msg'] = 'fail'
            return JsonResponse(res, status=500, safe=False)
    else:
        res['data'] = result[1]
        return JsonResponse(res, status=200, safe=False)


def get_bug_date(request, date):
    auto = cache.get("auto")
    auto_lis, manual_lis = [], []
    manual = cache.get("manual")
    j = 0
    for i in range(1, 13):
        if i + 4 > 12:
            if i == 9:
                start_date = datetime.datetime.strptime(f"{str(date)}-{str(i + 3)}-01", '%Y-%m-%d')
                end_date = datetime.datetime.strptime(f"{str(date + 1)}-1-01", '%Y-%m-%d') + datetime.timedelta(
                    hours=23, minutes=59, seconds=59)

            else:
                i = j + 1
                print(i)
                start_date = datetime.datetime.strptime(f"{str(date + 1)}-{str(i)}-01", '%Y-%m-%d')
                end_date = datetime.datetime.strptime(f"{str(date + 1)}-{str(i + 1)}-01",
                                                      '%Y-%m-%d') + datetime.timedelta(hours=23, minutes=59, seconds=59)
                j += 1
        else:
            start_date = datetime.datetime.strptime(f"{str(date)}-{str(i + 3)}-01", '%Y-%m-%d')
            end_date = datetime.datetime.strptime(f"{str(date)}-{str(i + 4)}-01", '%Y-%m-%d')
        lis = [item for item in auto[1]["bugs"] if
               start_date < datetime.datetime.strptime(item["creation_time"], '%Y-%m-%dT%H:%M:%SZ') < end_date]
        auto_lis.append(len(lis))
        lis = [item for item in manual[1]["bugs"] if
               start_date < datetime.datetime.strptime(item["creation_time"], '%Y-%m-%dT%H:%M:%SZ') < end_date]
        manual_lis.append(len(lis))
    print(auto_lis)
    total = 0
    res["data"] = {"auto": auto_lis, "manual": manual_lis, "count_auto": sum(auto_lis), "count_manual": sum(manual_lis)}
    return JsonResponse(res, status=200)


def get_month_bug(request, date, month):
    auto = cache.get("auto")
    auto_lis, manual_lis = [], []
    manual = cache.get("manual")
    j = 0
    import calendar
    month_days = calendar.mdays
    if month == 12:
        start_date = datetime.datetime.strptime(f"{str(date)}-{str(month)}-01", '%Y-%m-%d')
        end_date = datetime.datetime.strptime(f"{str(date + 1)}-01-01", '%Y-%m-%d') + datetime.timedelta(hours=23,
                                                                                                         minutes=59,
                                                                                                         seconds=59)
    else:
        start_date = datetime.datetime.strptime(f"{str(date)}-{str(month)}-01", '%Y-%m-%d')
        end_date = datetime.datetime.strptime(f"{str(date)}-{str(month + 1)}-01", '%Y-%m-%d') + datetime.timedelta(
            hours=23, minutes=59, seconds=59)
    autolis = [item for item in auto[1]["bugs"] if
               start_date < datetime.datetime.strptime(item["creation_time"], '%Y-%m-%dT%H:%M:%SZ') < end_date]
    manuallis = [item for item in manual[1]["bugs"] if
                 start_date < datetime.datetime.strptime(item["creation_time"], '%Y-%m-%dT%H:%M:%SZ') < end_date]
    print(month_days[month] + 1)
    for i in range(1, month_days[month] + 1):
        days = 0
        for item in autolis:
            if int(datetime.datetime.strptime(item["creation_time"], '%Y-%m-%dT%H:%M:%SZ').strftime("%d")) == i:
                days += 1
        auto_lis.append(days)
    for i in range(1, month_days[month] + 1):
        days = 0
        for item in manuallis:
            if int(datetime.datetime.strptime(item["creation_time"], '%Y-%m-%dT%H:%M:%SZ').strftime("%d")) == i:
                days += 1
        manual_lis.append(days)

    total = 0
    res["data"] = {"auto": auto_lis, "manual": manual_lis, "count_auto": sum(auto_lis), "count_manual": sum(manual_lis)}
    return JsonResponse(res, status=200, safe=False)


def get_week_bug(request):
    auto_lis, manual_lis, time_lis = [], [], []
    auto = cache.get("auto")
    manual = cache.get("manual")
    for i in get_week_list(datetime.datetime.now()):
        auto_list = [item for item in auto[1]["bugs"] if
                     i[0] < datetime.datetime.strptime(item["creation_time"], '%Y-%m-%dT%H:%M:%SZ') < i[-1]]
        manual_list = [item for item in manual[1]["bugs"] if
                       i[0] < datetime.datetime.strptime(item["creation_time"], '%Y-%m-%dT%H:%M:%SZ') < i[-1]]
        auto_lis.append(len(auto_list))
        manual_lis.append(len(manual_list))
        time_lis.append(f"{i[0].strftime('%m.%d')}-{i[-1].strftime('%m.%d')}")
    res['data'] = {'auto': auto_lis, 'manual': manual_lis, "time": time_lis}
    return JsonResponse(res, status=200, safe=False)


def get_bug_message_format(resp):
    result = []
    teams = ['Auto', 'Manual', 'Qtester']
    for team in teams:
        temp = {'Team': team}
        for key, value in resp.items():
            temp[key] = value[team.lower()]
        result.append(temp)
    return result


def get_bug_message(request):
    # total defect by release
    rest = {}
    effect_res = {}
    platform = settings.SEARCH_PLATFORM
    item = settings.SEARCH_ITEM
    start = request.GET.get('start')
    end = request.GET.get("end")
    start_date = datetime.datetime.strptime("2022-04-01", '%Y-%m-%d')
    start_date = datetime.datetime.strptime(start, '%Y-%m-%d') if start is not None else start_date
    end_date = datetime.datetime.now() + datetime.timedelta(hours=23, minutes=59, seconds=59)
    end_date = datetime.datetime.strptime(end, '%Y-%m-%d') + datetime.timedelta(hours=23, minutes=59,
                                                                                seconds=59) if end is not None else end_date
    for i in platform:
        dic = {}
        effective_dic = {}
        for j in item:
            n, m = 0, 0
            auto = cache.get(j)
            d_list = [item for item in auto[1]["bugs"] if
                      start_date < datetime.datetime.strptime(item["creation_time"], '%Y-%m-%dT%H:%M:%SZ') < end_date]
            for k in range(len(d_list)):
                if i in d_list[k]['version'] or str.lower(i) in d_list[k]['version'] or i in \
                        d_list[k]['summary'] or str.lower(i) in d_list[k]['summary'] or i in \
                        d_list[k]['platform'] or str.lower(i) in d_list[k]['platform']:
                    n += 1
                    if 'User Error' not in d_list[k]['resolution'] and "Hardware Fault" not in \
                            d_list[k][
                                'resolution'] and 'Working as Designed' not in d_list[k]['resolution']:
                        m += 1
            effective_dic[j] = m
            dic[j] = n
        rest[i] = dic
        effect_res[i] = effective_dic
    other, effective_other = {"Sustaining": {}, "Total": {}}, {"Sustaining": {}, "Total": {}}
    for j in item:
        auto = cache.get(j)
        num = 0
        d_list = [item for item in auto[1]["bugs"] if
                  start_date < datetime.datetime.strptime(item["creation_time"], '%Y-%m-%dT%H:%M:%SZ') < end_date]
        for k, v in rest.items():
            num += v[j]
        other['Sustaining'][j] = len(d_list) - num
        other['Total'][j] = len(d_list)
    rest = {"total_defects_by_releases": get_bug_message_format({**rest, **other})}

    # invalid_defects     Category by validity
    invalid_defects = {}
    category_by_validity = {"Invalid Defects": {}, "Effective Defects": {}, "Total": {}}
    for i in item:
        auto = cache.get(i)
        usererror, hd, workasd, other_count = 0, 0, 0, 0
        d_list = [item for item in auto[1]["bugs"] if
                  start_date < datetime.datetime.strptime(item["creation_time"], '%Y-%m-%dT%H:%M:%SZ') < end_date]
        for k in range(len(d_list)):
            if 'User Error' in d_list[k]['resolution']:
                usererror += 1
            elif "Hardware Fault" in d_list[k]['resolution']:
                hd += 1
            elif 'Working as Designed' in d_list[k]['resolution']:
                workasd += 1
            else:
                other_count += 1
        category_by_validity['Invalid Defects'][i] = usererror + workasd + hd
        category_by_validity["Effective Defects"][i] = other_count
        category_by_validity['Total'][i] = usererror + workasd + hd + other_count
        invalid_defects[i] = {"Working as Designed": workasd, "Hardware Fault": hd, "User Error": usererror,
                              "Total": workasd + hd + usererror}
    invalid_res = {"Working as Designed": {}, 'Hardware Fault': {}, 'User Error': {}, "Total": {}}
    for k, v in invalid_defects.items():
        invalid_res['Working as Designed'][k] = v['Working as Designed']
        invalid_res['Hardware Fault'][k] = v['Hardware Fault']
        invalid_res['User Error'][k] = v['User Error']
        invalid_res['Total'][k] = v['Total']
    # print(invalid_res)
    rest['invalid_defects'] = get_bug_message_format(invalid_res)
    rest['category_by_validity'] = get_bug_message_format(category_by_validity)

    # effective defect by releases
    effective_muanal, effective_auto, effective_qtester = 0, 0, 0
    for k, v in effect_res.items():
        effective_muanal += v['manual']
        effective_auto += v['auto']
        effective_qtester += v['qtester']
    sustaining_auto = category_by_validity['Effective Defects']['auto'] - effective_auto
    sustaining_manual = category_by_validity['Effective Defects']['manual'] - effective_muanal
    sustaining_qtester = category_by_validity['Effective Defects']['qtester'] - effective_qtester
    effect_res['Sustaining'] = {}
    for i in item:
        effect_res['Sustaining'][i] = eval(f'sustaining_{i}')
    effect_res['Total'] = category_by_validity['Effective Defects']
    rest['effective_defects_by_releases'] = get_bug_message_format(effect_res)
    res['data'] = rest
    return JsonResponse(res, status=200, safe=False)


def get_bug_message_detail(request):
    body = json.loads(request.body.decode())
    item_platform = body['item_platform']
    plat = item_platform.split("_")[1]
    platform = settings.SEARCH_PLATFORM
    item = item_platform.split("_")[0]
    auto = cache.get(item)
    mess = []
    sus_mess = []
    start = request.GET.get('start')
    end = request.GET.get("end")
    start_date = datetime.datetime.strptime("2022-04-01", '%Y-%m-%d')
    start_date = datetime.datetime.strptime(start, '%Y-%m-%d') if start is not None else start_date
    end_date = datetime.datetime.now() + datetime.timedelta(hours=23, minutes=59, seconds=59)
    end_date = datetime.datetime.strptime(end, '%Y-%m-%d') + datetime.timedelta(hours=23, minutes=59,
                                                                                seconds=59) if end is not None else end_date
    d_list = [item for item in auto[1]["bugs"] if
              start_date < datetime.datetime.strptime(item["creation_time"], '%Y-%m-%dT%H:%M:%SZ') < end_date]
    for k in range(len(d_list)):
        if plat != 'Sustaining' and plat != "Total":
            if plat in d_list[k]['version'] or str.lower(plat) in d_list[k]['version'] or plat in \
                    d_list[k]['summary'] or str.lower(plat) in d_list[k]['summary'] or plat in \
                    d_list[k]['platform'] or str.lower(plat) in d_list[k]['platform']:
                message = d_list[k]
                mess.append(
                    {"Id": message['id'], "Creator": message['creator'], 'Release': message['version'],
                     'Product': message['product'],
                     'Component': message['component'], 'Assignee': message['assigned_to'],
                     'Status': message['status'], 'Resolution': message['resolution'],
                     'Summary': message['summary'], 'Create_time': message['creation_time']})
        elif plat == "Sustaining":
            for i in platform:
                if d_list[k]['version'].find(i) != -1 or d_list[k]['version'].find(
                        str.lower(i)) != -1 or d_list[k]['summary'].find(i) != -1 or d_list[k][
                    'summary'].find(
                    str.lower(i)) != -1 or d_list[k]['platform'].find(i) != -1 or d_list[k][
                    'platform'].find(str.lower(i)) != -1:
                    d_list[k] = []
                    break
            if d_list[k]:
                message = d_list[k]
                mess.append(
                    {"Id": message['id'], "Creator": message['creator'], 'Release': message['version'],
                     'Product': message['product'],
                     'Component': message['component'], 'Assignee': message['assigned_to'],
                     'Status': message['status'], 'Resolution': message['resolution'],
                     'Summary': message['summary'], 'Create_time': message['creation_time']})
        elif plat == 'Total':
            message = d_list[k]
            mess.append(
                {"Id": message['id'], "Creator": message['creator'], 'Release': message['version'],
                 'Product': message['product'],
                 'Component': message['component'], 'Assignee': message['assigned_to'],
                 'Status': message['status'], 'Resolution': message['resolution'],
                 'Summary': message['summary'], 'Create_time': message['creation_time']})
    mess.reverse()
    page = request.GET.get('page', 1)
    # print(mess)
    page_size = request.GET.get('page_size', 10)
    paginator = Paginator(mess, page_size)
    try:
        current_page = paginator.page(page)
    except PageNotAnInteger:
        current_page = paginator.page(1)
    except EmptyPage:
        current_page = paginator.page(paginator.num_pages)
    res['data'] = {"list": current_page.object_list, "pages": len(mess)}
    return JsonResponse(res, status=200, safe=False)


def bug_rank_list(request):
    if request.method == "GET":
        auto = cache.get("auto")
        manual = cache.get("manual")
        start = request.GET.get('start')
        end = request.GET.get("end")
        start_date = datetime.datetime.now() - datetime.timedelta(days=30)
        start_date = datetime.datetime.strptime(start, '%Y-%m-%d') if start is not None else start_date
        end_date = datetime.datetime.now() + datetime.timedelta(hours=23, minutes=59, seconds=59)
        end_date = datetime.datetime.strptime(end, '%Y-%m-%d') + datetime.timedelta(hours=23, minutes=59,
                                                                                    seconds=59) if end is not None else end_date
        '''
        report lis
        '''
        lis = [
            [item['creator'], item['status'], {"Id": item['id'], "Creator": item['creator'], 'Release': item['version'],
                                               'Product': item['product'],
                                               'Component': item['component'], 'Assignee': item['assigned_to'],
                                               'Status': item['status'], 'Resolution': item['resolution'],
                                               'Summary': item['summary'], 'Create_time': item['creation_time']}] for
            item in auto[1]["bugs"] if
            start_date < datetime.datetime.strptime(
                item["creation_time"], '%Y-%m-%dT%H:%M:%SZ') < end_date]
        manual_lis = [
            [item['creator'], item['status'], {"Id": item['id'], "Creator": item['creator'], 'Release': item['version'],
                                               'Product': item['product'],
                                               'Component': item['component'], 'Assignee': item['assigned_to'],
                                               'Status': item['status'], 'Resolution': item['resolution'],
                                               'Summary': item['summary'], 'Create_time': item['creation_time']}] for
            item in manual[1]["bugs"] if
            start_date < datetime.datetime.strptime(
                item["creation_time"], '%Y-%m-%dT%H:%M:%SZ') < end_date]
        lis += manual_lis
        dic, ownerlis = {i[1]: 0 for i in lis}, list(set([i[0] for i in lis]))
        dic['detail'] = []
        creator_data = []
        for owner in ownerlis:
            num = 0
            while num < len(lis):
                if owner == lis[num][0]:
                    dic[lis[num][1]] += 1
                    dic["owner"] = owner.split("@")[0]
                    dic['detail'].append(lis[num][2])
                num += 1
            else:
                count = 0
                for k, v in dic.items():
                    if k != "owner" and k != 'detail': count += v
                dic['count'] = count
                creator_data.append(dic)
                dic = {j[1]: 0 for j in lis}
                dic['detail'] = []
                continue
        creator_data = sorted(creator_data, key=lambda x: x['count'], reverse=True)
        '''
        assignee list
        '''
        xcc = cache.get('xcc')
        uefi = cache.get('uefi')
        all_lis = [[[item['assigned_to'], item['status'],
                     {"Id": item['id'], "Creator": item['creator'], 'Release': item['version'],
                      'Product': item['product'],
                      'Component': item['component'], 'Assignee': item['assigned_to'],
                      'Status': item['status'], 'Resolution': item['resolution'],
                      'Summary': item['summary'], 'Create_time': item['creation_time']}] for item in xcc[1]["bugs"] if
                    start_date < datetime.datetime.strptime(
                        item["creation_time"], '%Y-%m-%dT%H:%M:%SZ') < end_date],
                   [[item['assigned_to'], item['status'],
                     {"Id": item['id'], "Creator": item['creator'], 'Release': item['version'],
                      'Product': item['product'],
                      'Component': item['component'], 'Assignee': item['assigned_to'],
                      'Status': item['status'], 'Resolution': item['resolution'],
                      'Summary': item['summary'], 'Create_time': item['creation_time']}] for item in uefi[1]["bugs"] if
                    start_date < datetime.datetime.strptime(
                        item["creation_time"], '%Y-%m-%dT%H:%M:%SZ') < end_date]]
        assignee_data_dict = {}
        team = "xcc"
        for lis in all_lis:
            dic, ownerlis = {i[1]: 0 for i in lis}, list(set([i[0] for i in lis]))
            dic['detail'] = []
            assignee_data = []
            for owner in ownerlis:
                num = 0
                while num < len(lis):
                    if owner == lis[num][0]:
                        dic[lis[num][1]] += 1
                        dic["owner"] = owner.split("@")[0]
                        dic['detail'].append(lis[num][2])
                    num += 1
                else:
                    count = 0
                    for k, v in dic.items():
                        if k != "owner" and k != "detail": count += v
                    dic['count'] = count
                    assignee_data.append(dic)
                    dic = {j[1]: 0 for j in lis}
                    dic['detail'] = []
                    continue
            assignee_data = sorted(assignee_data, key=lambda x: x['count'], reverse=True)
            assignee_data_dict[team] = assignee_data
            team = 'uefi'

        res['data'] = {'creator': creator_data, 'assignee': assignee_data_dict}

    return JsonResponse(res, safe=False)


def high_level_bug(request):
    if request.method == "GET":
        auto = cache.get("auto")
        manual = cache.get("manual")
        start = request.GET.get('start')
        end = request.GET.get("end")
        start_date = datetime.datetime.now() - datetime.timedelta(days=30)
        start_date = datetime.datetime.strptime(start, '%Y-%m-%d') if start is not None else start_date
        end_date = datetime.datetime.now() + datetime.timedelta(hours=23, minutes=59, seconds=59)
        end_date = datetime.datetime.strptime(end, '%Y-%m-%d') + datetime.timedelta(hours=23, minutes=59,
                                                                                    seconds=59) if end is not None else end_date
        '''
        report lis
        '''
        lis = [
            {"Id": item['id'], "Creator": item['creator'], 'Release': item['version'],
             'Product': item['product'],
             'Component': item['component'], 'Assignee': item['assigned_to'],
             'Status': item['status'], 'Resolution': item['resolution'],
             'Summary': item['summary'], 'Create_time': item['creation_time'], 'severity': item['severity']} for
            item in auto[1]["bugs"] if
            start_date < datetime.datetime.strptime(
                item["creation_time"], '%Y-%m-%dT%H:%M:%SZ') < end_date and item['severity'] == 'High' and item[
                'status'] != 'Closed']
        manual_lis = [
            {"Id": item['id'], "Creator": item['creator'], 'Release': item['version'],
             'Product': item['product'],
             'Component': item['component'], 'Assignee': item['assigned_to'],
             'Status': item['status'], 'Resolution': item['resolution'],
             'Summary': item['summary'], 'Create_time': item['creation_time'], 'severity': item['severity']} for
            item in manual[1]["bugs"] if
            start_date < datetime.datetime.strptime(
                item["creation_time"], '%Y-%m-%dT%H:%M:%SZ') < end_date and item['severity'] == 'High' and item[
                'status'] != 'Closed']
        lis += manual_lis
        res['data'] = {'high': lis}

    return JsonResponse(res, safe=False)
