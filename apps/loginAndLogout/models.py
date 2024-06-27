from datetime import datetime

from django.db import models

# Create your models here.


class Eventlog(models.Model):
    id = models.AutoField(primary_key=True)
    events = models.CharField(max_length=128, verbose_name="events")  # event
    result = models.CharField(max_length=64, verbose_name="members")
    createtime = models.DateTimeField(default=datetime.now, verbose_name="createtime")
    userid = models.ForeignKey('auth.user', to_field='id', on_delete=models.CASCADE)