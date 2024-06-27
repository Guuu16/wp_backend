from django.db import models
from datetime import datetime


# Create your models here.


class HostInfo1(models.Model):
    id = models.AutoField(primary_key=True)
    IMMIP = models.CharField(max_length=32, verbose_name="IMMIP")  # immip
    IMMUSER = models.CharField(max_length=32, verbose_name="IMMUSER", null=True)
    IMMPASSWORD = models.CharField(max_length=32, verbose_name="IMMPASSWORD", null=True)
    OSIP = models.CharField(max_length=32, verbose_name="OSIP", null=True)
    OSUSER = models.CharField(max_length=32, verbose_name="OSUSER", null=True)
    OSPASSWORD = models.CharField(max_length=32, verbose_name="OSPASSWORD", null=True)
    Category = models.CharField(max_length=32, verbose_name="Category", null=True)
    Name = models.CharField(max_length=32, verbose_name="Name", null=True)
    Location = models.CharField(max_length=64, verbose_name="Location", null=True)
    Host_SN = models.CharField(max_length=64, verbose_name="Host_SN", null=True)
    Comments = models.CharField(max_length=512, verbose_name="Comments", null=True)
    User = models.CharField(max_length=32, verbose_name="User", null=True)
    Owner = models.CharField(max_length=32, verbose_name="Owner", null=True)
    Host_Status = models.CharField(max_length=16, verbose_name="Host_Status", null=True)  # free broken
    Tag = models.CharField(max_length=16, verbose_name="Tag", null=True)
    PDU = models.CharField(max_length=64, verbose_name="PDU", null=True)
    PDU_Port = models.CharField(max_length=64, verbose_name="PDU_Port", null=True)
    Sw_Config = models.CharField(max_length=64, verbose_name="Sw_Config", null=True)
    Hw_Config = models.CharField(max_length=64, verbose_name="Hw_Config", null=True)
    createtime = models.DateTimeField(default=datetime.now, verbose_name="createtime")
    updatetime = models.DateTimeField(auto_now=True, verbose_name="updatetime")


class HardWare1(models.Model):
    id = models.AutoField(primary_key=True)
    BMCIP = models.ForeignKey('Hostinfo1', to_field='id',related_name="hostinfo_id", on_delete=models.CASCADE)  # BMCIP
    Machine = models.CharField(max_length=64, verbose_name="Machine", null=True)
    CPU_Name = models.CharField(max_length=256, verbose_name="CPU_Name", null=True)
    CPU_Current_Num = models.CharField(max_length=64, verbose_name="CPU_Current_Num", null=True)
    CPU_Max_Num = models.CharField(max_length=64, verbose_name="CPU_Max_Num", null=True)
    DIMM_Name = models.CharField(max_length=128, verbose_name="DIMM_Name", null=True)
    DIMM_Current_Num = models.CharField(max_length=64, verbose_name="DIMM_Current_Num", null=True)
    DIMM_Max_Num = models.CharField(max_length=64, verbose_name="DIMM_Max_Num", null=True)
    DIMM_Source_enough = models.CharField(max_length=16, verbose_name="DIMM_Source_enough", null=True)
    DIMM_Subcatrgory = models.CharField(max_length=16, verbose_name="DIMM_Subcatrgory", null=True)
    PSU_Power = models.CharField(max_length=128, verbose_name="PSU_Power", null=True)
    PSU_Current_Num = models.CharField(max_length=64, verbose_name="PSU_Current_Num", null=True)
    PSU_Max_Num = models.CharField(max_length=64, verbose_name="PSU_Max_Num", null=True)
    RAID_Name = models.CharField(max_length=128, verbose_name="RAID_Name", null=True)
    RAID_Current_Num = models.CharField(max_length=64, verbose_name="RAID_Current_Num", null=True)
    HDD_Capacity = models.CharField(max_length=128, verbose_name="HDD_Capacity", null=True)
    HDD_Current_Num = models.CharField(max_length=64, verbose_name="HDD_Current_Num", null=True)
    HDD_Max_Num = models.CharField(max_length=64, verbose_name="HDD_Max_Num", null=True)
    OtherCards_Name = models.CharField(max_length=128, verbose_name="OtherCards_Name", null=True)
    OtherCards_Current_Num = models.CharField(max_length=64, verbose_name="OtherCards_Current_Num", null=True)
    Comment = models.CharField(max_length=512, verbose_name="Comment", null=True)
    updatetime = models.DateTimeField(auto_now=True, verbose_name="updatetime")


class ConfigMessage(models.Model):
    id = models.AutoField(primary_key=True)
    Config_name = models.CharField(max_length=128, verbose_name="config_name", null=True)
    Config_message = models.TextField(max_length=12288, verbose_name="config_message",null=True)
    ConfigId = models.ForeignKey('Hostinfo1', to_field='id', related_name="config_id", on_delete=models.CASCADE)


class CommonConfigMessage(models.Model):
    id = models.AutoField(primary_key=True)
    CommonConfigName = models.CharField(max_length=32, verbose_name="CommonConfigName", null=True)
    CommonConfig_message = models.TextField(max_length=12288, verbose_name="CommonConfig_message",null=True)
    createtime = models.DateTimeField(default=datetime.now, verbose_name="createtime")
    updatetime = models.DateTimeField(auto_now=True, verbose_name="updatetime")