from django.db import models
from datetime import datetime


# Create your models here.
class User(models.Model):
    user = models.CharField(max_length=255, verbose_name="user")  # Jenkins Job Fullname
    auto_or_manual = models.CharField(max_length=20, verbose_name="auto_or_manual")
    createtime = models.DateTimeField(default=datetime.now, verbose_name="create_time")
    updatetime = models.DateTimeField(auto_now=True, verbose_name="update_time")

