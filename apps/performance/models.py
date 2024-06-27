from django.db import models


# Create your models here.
class Cases(models.Model):
    id = models.AutoField(primary_key=True)
    case_name = models.CharField(max_length=255, verbose_name="case_name")


class HostSWInfo(models.Model):
    id = models.AutoField(primary_key=True)
    job_id = models.CharField(max_length=32, null=False)
    release = models.CharField(max_length=64, null=False)
    before_xcc = models.CharField(max_length=64)
    before_uefi = models.CharField(max_length=64)
    before_lxpm = models.CharField(max_length=64)
    current_xcc = models.CharField(max_length=64, null=False)
    current_uefi = models.CharField(max_length=64, null=False)
    current_lxpm = models.CharField(max_length=64, null=False)
    before_pfr = models.CharField(max_length=64)
    current_pfr = models.CharField(max_length=64, null=False)
    before_fpga = models.CharField(max_length=64)
    current_fpga = models.CharField(max_length=64, null=False)
    before_me = models.CharField(max_length=64)
    current_me = models.CharField(max_length=64)


class HostHWInfo(models.Model):
    id = models.AutoField(primary_key=True)
    job_id = models.CharField(max_length=32, null=False)
    machine_type = models.CharField(max_length=64)
    platform_name = models.CharField(max_length=64)
    bmc_ip = models.CharField(max_length=32)
    bmc_mac = models.CharField(max_length=64)
    cpu_num = models.IntegerField()
    cpu_info = models.TextField()
    mem_num = models.IntegerField()
    mem_info = models.TextField()
    pcie_num = models.IntegerField()
    pcie_info = models.TextField()
    hdd_num = models.IntegerField(null=True)
    hdd_info = models.TextField()
    smbios = models.CharField(max_length=32)
    mb_phase = models.CharField(max_length=32)


class Performance(models.Model):
    id = models.AutoField(primary_key=True)
    job_id = models.CharField(max_length=32)
    date = models.DateTimeField()
    perf_category = models.CharField(max_length=64)
    ffdc_times = models.IntegerField(null=True)
    real_times = models.IntegerField(null=True)
    boot_mode = models.CharField(max_length=32)
    host_hw_info_id = models.ForeignKey('HostHWInfo', to_field='id', on_delete=models.CASCADE)
    host_sw_info_id = models.ForeignKey('HostSWInfo', to_field='id', on_delete=models.CASCADE)
    case_name_id = models.ForeignKey('Cases', to_field='id', on_delete=models.CASCADE)
