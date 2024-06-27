from django.db import models
from datetime import datetime
import jwt
from webportal import settings, util
from django.utils import timezone


# Create your models here.


class Task2(models.Model):
    id = models.AutoField(primary_key=True)
    jobname = models.CharField(max_length=255, verbose_name="jobname")  # Jenkins Job Fullname
    release = models.CharField(max_length=32, verbose_name="release")
    params = models.TextField(verbose_name="params")
    build_number = models.IntegerField(verbose_name="build_number")
    building = models.BooleanField(verbose_name="building")
    url = models.TextField(verbose_name="url")
    username = models.CharField(max_length=32, verbose_name="username")
    userid = models.CharField(max_length=32, verbose_name="userid")
    short_description = models.CharField(max_length=32, verbose_name="short_description")
    result = models.CharField(max_length=32, verbose_name="result")
    createtime = models.DateTimeField(default=datetime.now, verbose_name="createtime")
    updatetime = models.DateTimeField(auto_now=True, verbose_name="updatetime")
    content = models.TextField(verbose_name="content")
    source = models.IntegerField(default=0, verbose_name="source")  # 0 xpit, 1 daily


class Group(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, verbose_name="name")  # Jenkins Job Fullname
    members = models.CharField(max_length=512, verbose_name="members")
    userid = models.ForeignKey('auth.user', to_field='id', on_delete=models.CASCADE)
    createtime = models.DateTimeField(default=datetime.now, verbose_name="createtime")
    updatetime = models.DateTimeField(auto_now=True, verbose_name="updatetime")


class Host(models.Model):
    id = models.AutoField(primary_key=True)
    immip = models.CharField(max_length=32, verbose_name="immip")
    build_number = models.ForeignKey('Task2', to_field='id', on_delete=models.CASCADE)
    createtime = models.DateTimeField(default=datetime.now, verbose_name="createtime")
    updatetime = models.DateTimeField(auto_now=True, verbose_name="updatetime")


class StressTask(models.Model):
    id = models.AutoField(primary_key=True)
    build_number = models.IntegerField(verbose_name="build_number")
    system = models.CharField(max_length=32, verbose_name="system")
    release = models.CharField(max_length=32, verbose_name="release")
    immip = models.CharField(max_length=32, verbose_name="immip")
    info = models.TextField(verbose_name="info")
    entry_taskid = models.ForeignKey('Task2', to_field='id', on_delete=models.CASCADE)
    createtime = models.DateTimeField(default=datetime.now, verbose_name="createtime")


class TaskEmailDetail(models.Model):
    id = models.AutoField(primary_key=True)
    taskid = models.ForeignKey('Task2', to_field='id', on_delete=models.CASCADE)
    build_number = models.IntegerField(verbose_name="build_number")
    jobname = models.CharField(max_length=64, verbose_name="jobname")
    emaildetail = models.TextField(max_length=8192, verbose_name="emaildetail")
    createtime = models.DateTimeField(default=datetime.now, verbose_name="createtime")


class TaskSchedule(models.Model):
    id = models.AutoField(primary_key=True)
    enabled = models.BooleanField(default=True)
    schedule_time = models.DateTimeField(verbose_name="schedule_time")
    total = models.IntegerField(verbose_name="total")
    count = models.IntegerField(verbose_name="count", default=0)
    weekdays = models.IntegerField(verbose_name="weekdays")  # use `util.bits_from`
    jobname = models.CharField(max_length=255, verbose_name="jobname")  # Jenkins Job Fullname
    params = models.TextField(verbose_name="params")
    userid = models.ForeignKey('auth.user', to_field='id', on_delete=models.CASCADE)
    username = models.CharField(max_length=32, verbose_name="username")
    release = models.CharField(max_length=32, verbose_name="release")
    source = models.IntegerField(default=0, verbose_name="source")  # 0 xpit, 1 daily
    createtime = models.DateTimeField(default=datetime.now, verbose_name="createtime")
    updatetime = models.DateTimeField(auto_now=True, verbose_name="updatetime")

    @classmethod
    def queryActiveSchedulers(cls):
        schedulers = cls.objects.filter(enabled=True, schedule_time__lte=timezone.now())
        active_schedulers = []
        for scheduler in schedulers:
            scheduler.refresh_from_db()
            total = getattr(scheduler,"total")
            if scheduler.count < total:
                active_schedulers.append(scheduler)
        return active_schedulers
        # return cls.objects.filter(enabled=True, scheduletime__lte=timezone.now(), count__lt=cls.total)

    def scheduleNext(self):
        self.count += 1
        self.scheduletime = util.getScheduletime(self.weekdays, dateobj=self.schedule_time)
        self.save()
