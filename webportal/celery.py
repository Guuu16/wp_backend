# -*- coding: utf-8 -*-
"""
@Time ： 6/25/23 10:05 AM
@Auth ： gujie5
"""
# celery.py
# 在django项目setting文件的同级目录下建一个celery.py文件
# celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab
from webportal.settings import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

# 设置默认Django settings模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webportal.settings')
app = Celery('webportal', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)
# 使用django配置文件进行Celery配置
app.config_from_object('django.conf:settings', namespace='CELERY')
# 从所有已注册的app中加载任务模块
# app.autodiscover_tasks()
app.autodiscover_tasks([
    'apps.machine.machine_operation.tasks.set_machine_status',
    'apps.jenkinsServer.jenkins_server.tasks.poll_schedule_task'
])
app.conf.update(
    CELERYBEAT_SCHEDULE={
        'bugs_redis': {
            'task': 'apps.bugzila.bugzila_server.test_crontab.bugs_redis',
            'schedule': crontab(minute="*/15"),  # bug 15min /1
            'args': (),
        },
        'pa_qtester_redis': {
            'task': 'apps.bugzila.bugzila_server.test_crontab.pa_qtester_redis',
            'schedule': crontab(minute="*/15"),  # bug 15min /1
            'args': (),
        },
        'set_machine_status': {
            'task': 'apps.machine.machine_operation.tasks.set_machine_status',
            'schedule': crontab(minute="*/6"),  # 2:00 /1
            'args': (),
        },
        'sync_jenkins_jobs': {
            'task': 'apps.jenkinsServer.jenkins_server.tasks.sync_jenkins_jobs',
            'schedule': crontab(minute="*/3"),  # jenkins job 3min/1
            'args': (),
        },
        'poll_task_state': {
            'task': 'apps.jenkinsServer.jenkins_server.tasks.poll_task_state',
            'schedule': crontab(minute="*/3"),  # jenkins job 3min/1
            'args': (),
        },
        'get_all_workmate': {
            'task': 'apps.bugzila.bugzila_server.test_crontab.get_all_workmate',
            'schedule': crontab(hour=2),  # 2:00 /1
            'args': (),
        },
        'poll_schedule_task': {
            'task': 'apps.jenkinsServer.jenkins_server.tasks.poll_schedule_task',
            'schedule': crontab(minute="*/3"),  # jenkins job 3min/1
            'args': (),
        },
    }

)
