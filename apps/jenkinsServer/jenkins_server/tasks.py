# -*- coding: utf-8 -*-
"""
@Time ： 1/13/23 5:31 PM
@Auth ： gujie5
"""
import json
import logging
import os, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webportal.settings')
django.setup()
from celery import shared_task
from django.core.cache import cache
from webportal import settings
from jenkinsServer.models import Task2 as Task
from jenkinsServer.models import TaskSchedule
from datetime import datetime

from apps.jenkinsServer.jenkins_server.jenkins_backend import getServer


@shared_task
def sync_jenkins_jobs():
    # fecth & transform job info
    server = getServer()
    jobs = {}
    pit_jobs = jobs["mrt"] = []
    xpit_jobs = jobs["xpit"] = []
    daily_jobs = jobs["daily"] = []
    uEfi_jobs = jobs["UEFI"] = []
    stress_jobs = jobs["memorystress"] = []
    performance_jobs = jobs["performance"] = []
    for job in server.get_all_jobs():
        jname = job["name"].lower()
        if jname.startswith("xpit_"):
            xpit_jobs.append(job)
        elif jname.startswith("performance_"):
            performance_jobs.append(job)
        elif jname.startswith("mrt_"):
            pit_jobs.append(job)
        elif jname.startswith('daily_'):
            daily_jobs.append(job)
        elif jname.endswith('uefi'):
            uEfi_jobs.append(job)
        elif jname.startswith("memorystress_"):  # memory stress
            stress_jobs.append(job)

    def handle_jobs(jobs):
        for job in jobs:
            job_info = server.get_job_info(job['fullname'])
            # print(job_info)
            params = []
            # transvers across array: property&actions
            for action in job_info["actions"]:
                if "parameterDefinitions" in action:
                    # print(action["parameterDefinitions"])
                    params.extend(action["parameterDefinitions"])
            for prop in job_info["property"]:

                if "parameterDefinitions" in prop:
                    # print(prop["parameterDefinitions"])
                    params.extend(prop["parameterDefinitions"])

            job["params"] = params

    handle_jobs(pit_jobs)
    handle_jobs(xpit_jobs)
    handle_jobs(daily_jobs)
    handle_jobs(uEfi_jobs)
    handle_jobs(stress_jobs)
    handle_jobs(performance_jobs)
    # set cache
    cache.set("jobs", jobs, settings.NEVER_REDIS_TIMEOUT)
    return jobs


@shared_task
def poll_task_state():
    server = getServer()
    print(f"start to update task time: {datetime.now()}")
    for task in Task.objects.filter(building=True):
        try:
            info = server.get_build_info(task.jobname, task.build_number)
        except Exception:
            continue
        if not info["building"]:
            print(datetime.now())
            Task.objects.filter(id=task.id).update(building=info["building"], result=info["result"],
                                                   updatetime=datetime.now())

@shared_task
def poll_schedule_task():
    server = getServer()
    for tser in TaskSchedule.queryActiveSchedulers():
        username = tser.username
        params = {k: v for k, v in json.loads(tser.params).items()}
        jobname = tser.jobname
        buildNumber, msg = server.buildJob(jobname, params)
        if buildNumber < 0:
            res = {"success": False, "error": msg}
            logging.error("------------------%s" % res)
        else:
            buildInfo = server.get_build_info(jobname, buildNumber)
            task = Task()
            task.jobname = jobname
            task.build_number = buildNumber
            task.building = buildInfo["building"]
            task.url = settings.JENKINS_URL + buildInfo["url"].split("/", 3)[-1]
            task.result = "START"
            task.username = username
            task.userid = username
            task.release = tser.release
            task.source = tser.source
            task.params = json.dumps(params)
            task.save()
            msg = {"userid": tser.userid,
                   "event": "Trigger Task: %s(#%s)" % (jobname, buildNumber),
                   "result": "SUCCESS"}
            logging.info("---------------------%s" % msg)
            tser.scheduleNext()


def opt_job(data, jobname):
    jobs = data[jobname]
    # xPIT22B/xpit_22b_entry
    # id: release, eg: 22b, amd
    # systemOptions: platform, eg: cyborg
    # testItems:     test items, eg: flash_fw_build
    options = {'releaseOptions': [], "p": jobname}
    if jobname == "xpit":
        for job in jobs:
            release = job['name'].split('_', 2)[1]
            sysOpts = []
            testItems = []
            for param in job['params']:
                if param['name'].endswith('_SYS'):
                    sysOpts.append(param['name'][:~3])
                elif param['name'].endswith('_LOOP'):
                    testItems.append(param['name'][:~4])
                elif param['name'].endswith("_DOCKER") or param['name'] == "DRAFT":
                    testItems.append(param['name'])
            options["releaseOptions"].append(
                {"text": release, "id": release, "systemOptions": sysOpts, "testItems": testItems})
    elif jobname == "daily":
        for job in jobs:
            product, release = job['name'].split('_', 2)[:2]
            xtestItems = []
            utestItems = []
            sysOpts = []
            prefix = job["name"][:~5]
            for param in job['params']:
                if param['name'].endswith('_XTEST'):
                    xtestItems.append(param['name'][:~5])
                elif param['name'].endswith("_DOCKER") or param['name'] == "DRAFT":
                    xtestItems.append(param['name'])
                elif param['name'].endswith('_UTEST'):
                    utestItems.append(param['name'][:~5])
                elif param['name'].endswith('_SYS'):
                    sysOpts.append(param['name'][:~3])
            options["releaseOptions"].append({
                "text": prefix, "id": prefix,
                "testItems": {'xcc': xtestItems, 'uefi': utestItems},
                "systemOptions": sysOpts
            })
    elif jobname == "mrt":
        for job in jobs:
            product, release = job['name'].split('_', 2)[:2]
            xtestItems = []
            utestItems = []
            sysOpts = []
            prefix = job["name"][:~3]
            for param in job['params']:
                if param['name'].endswith('_XTEST'):
                    xtestItems.append(param['name'][:~5])
                elif param['name'].endswith("_DOCKER") or param['name'] == "DRAFT":
                    xtestItems.append(param['name'])
                elif param['name'].endswith('_UTEST'):
                    utestItems.append(param['name'][:~5])
                elif param['name'].endswith('_SYS'):
                    sysOpts.append(param['name'][:~3])
            options["releaseOptions"].append({
                "text": prefix, "id": prefix,
                "testItems": {'xcc': xtestItems, 'uefi': utestItems},
                "systemOptions": sysOpts
            })
    elif jobname == "UEFI":
        for job in jobs:
            release = job['name'].split('_', 2)[1]
            sysOpts = []
            testItems = []
            for param in job['params']:
                if param['name'].endswith('_SYS'):
                    sysOpts.append(param['name'][:~3])
                elif param['name'].endswith('_TEST'):
                    testItems.append(param['name'][:~4])
                elif param['name'].endswith("_DOCKER") or param['name'] == "DRAFT":
                    testItems.append(param['name'])
            options["releaseOptions"].append(
                {"text": release, "id": release, "systemOptions": sysOpts, "testItems": testItems})
    elif jobname == "memorystress":
        for job in jobs:
            product, release = job['name'].split('_', 2)[:2]
            xtestItems = []
            utestItems = []
            stressItems = []
            sysOpts = []
            prefix = job["name"][:~3]
            for param in job['params']:
                if param['name'].endswith('_XTEST'):
                    xtestItems.append(param['name'][:~5])
                elif param['name'].endswith('_UTEST'):
                    utestItems.append(param['name'][:~5])
                elif param['name'].endswith('_SYS'):
                    sysOpts.append(param['name'][:~3])
                elif param["name"].endswith("_MTEST"):
                    stressItems.append(param["name"][:~3])

            options["releaseOptions"].append({
                "text": release, "id": release,
                "testItems": stressItems,
                "systemOptions": sysOpts
            })
    elif jobname == "performance":
        for job in jobs:
            release = job['name'].split('_', 2)[1]
            sysOpts = []
            testItems = []
            for param in job['params']:
                if param['name'].endswith('_SYS'):
                    sysOpts.append(param['name'][:~3])
                elif param['name'].endswith('_LOOP'):
                    testItems.append(param['name'][:~4])
                elif param['name'].endswith("_DOCKER") or param['name'] == "DRAFT":
                    testItems.append(param['name'])
            options["releaseOptions"].append(
                {"text": release, "id": release, "systemOptions": sysOpts, "testItems": testItems})
    # sorting
    # alph first sort by asc
    # digit second sort by desc
    digs = []
    alps = []
    for opt in options['releaseOptions']:
        if opt['id'][0].isdigit():
            digs.append(opt)
        else:
            alps.append(opt)
    # Will sort releases by id
    options['releaseOptions'] = sorted(alps, key=lambda x: x["id"]) + sorted(digs, key=lambda x: x["id"], reverse=True)
    return options


def option_job(data, jobname):
    jobs = data[jobname]
    # xPIT22B/xpit_22b_entry
    # id: release, eg: 22b, amd
    # systemOptions: platform, eg: cyborg
    # testItems:     test items, eg: flash_fw_build
    options = {'releaseOptions': [], "p": jobname}
    dic = {}
    for job in jobs: dic[job['name'].split("_")[1]] = []
    [dic[job['name'].split("_")[1]].append(job['name'].split("_", 2)[-1]) for job in jobs]
    if jobname == "mrt":
        i = 0
        while i < len(jobs):
            xtestItems = []
            utestItems = []
            loopItems = []
            if i == 0 or jobs[i]['name'].split("_")[1] != jobs[i - 1]['name'].split("_")[1]:
                prefix = jobs[i]["name"].split("_")[1]
                for param in jobs[i]['params']:
                    print(param)
                    if param['name'].endswith('_XTEST'):
                        xtestItems.append(param['name'][:~5])
                    elif param['name'].endswith("_DOCKER") or param['name'] == "DRAFT":
                        xtestItems.append(param['name'])
                    elif param['name'].endswith('_UTEST'):
                        utestItems.append(param['name'][:~5])
                    elif param['name'].endswith("_STEST"):
                        loopItems.append(param['name'][:~5])
                options["releaseOptions"].append({
                    "text": prefix, "id": prefix,
                    "testItems": {'xcc': xtestItems, 'uefi': utestItems, "stress": loopItems},
                    "systemOptions": dic[prefix]
                })
            i += 1
    elif jobname == "daily":
        i = 0
        while i < len(jobs):
            xtestItems = []
            utestItems = []
            if i == 0 or jobs[i]['name'].split("_")[1] != jobs[i - 1]['name'].split("_")[1]:
                prefix = jobs[i]["name"].split("_")[1]
                for param in jobs[i]['params']:
                    # print(param)
                    if param['name'].endswith('_XTEST'):
                        xtestItems.append(param['name'][:~5])
                    elif param['name'].endswith("_DOCKER") or param['name'] == "DRAFT":
                        xtestItems.append(param['name'])
                    elif param['name'].endswith('_UTEST'):
                        utestItems.append(param['name'][:~5])
                options["releaseOptions"].append({
                    "text": prefix, "id": prefix,
                    "testItems": {'xcc': xtestItems, 'uefi': utestItems},
                    "systemOptions": dic[prefix]
                })
            i += 1
    elif jobname == "xpit":
        i = 0
        while i < len(jobs):
            testItems = []
            if i == 0 or jobs[i]['name'].split("_")[1] != jobs[i - 1]['name'].split("_")[1]:
                prefix = jobs[i]["name"].split("_")[1]
                for param in jobs[i]['params']:
                    print(param)
                    if param['name'].endswith('_STEST'):
                        testItems.append(param['name'][:~5])
                    elif param['name'].endswith("_DOCKER") or param['name'] == "DRAFT":
                        testItems.append(param['name'])
                options["releaseOptions"].append({
                    "text": prefix, "id": prefix,
                    "testItems": testItems,
                    "systemOptions": dic[prefix]
                })
            i += 1
    elif jobname == "performance":
        i = 0
        while i < len(jobs):
            testItems = []
            if i == 0 or jobs[i]['name'].split("_")[1] != jobs[i - 1]['name'].split("_")[1]:
                prefix = jobs[i]["name"].split("_")[1]
                for param in jobs[i]['params']:
                    print(param)
                    if param['name'].endswith('_PTEST'):
                        testItems.append(param['name'][:~5])
                    elif param['name'].endswith("_DOCKER") or param['name'] == "DRAFT":
                        testItems.append(param['name'])
                options["releaseOptions"].append({
                    "text": prefix, "id": prefix,
                    "testItems": testItems,
                    "systemOptions": dic[prefix]
                })
            i += 1
    elif jobname == "memorystress":
        i = 0
        while i < len(jobs):
            testItems = []
            if i == 0 or jobs[i]['name'].split("_")[1] != jobs[i - 1]['name'].split("_")[1]:
                prefix = jobs[i]["name"].split("_")[1]
                for param in jobs[i]['params']:
                    print(param)
                    if param['name'].endswith('_MTEST'):
                        testItems.append(param['name'][:~5])
                    elif param['name'].endswith("_DOCKER") or param['name'] == "DRAFT":
                        testItems.append(param['name'])
                options["releaseOptions"].append({
                    "text": prefix, "id": prefix,
                    "testItems": testItems,
                    "systemOptions": dic[prefix]
                })
            i += 1
    # sorting
    # alph first sort by asc
    # digit second sort by desc
    digs = []
    alps = []
    for opt in options['releaseOptions']:
        if opt['id'][0].isdigit():
            digs.append(opt)
        else:
            alps.append(opt)
    # Will sort releases by id
    options['releaseOptions'] = sorted(alps, key=lambda x: x["id"]) + sorted(digs, key=lambda x: x["id"], reverse=True)
    return options


if __name__ == '__main__':
    poll_schedule_task()
