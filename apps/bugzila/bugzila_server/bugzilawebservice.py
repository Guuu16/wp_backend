# -*- coding: utf-8 -*-
"""
@Time ： 1/12/23 2:10 PM
@Auth ： gujie5
"""
from apps.bugzila.bugzila_server import bugs
import comments


class BugzillaBase:
    def __init__(self, url_base, token):
        self.url_base = url_base
        self.token = token

    def set_url_base(self, url_base):
        self.url_base = url_base


class BugzillaWebService(BugzillaBase):
    '''
        The REST API for creating, changing, and getting the details of bugs.
        This part of the Bugzilla REST API allows you to file new bugs in Bugzilla and to get information about existing bugs.
        View details please visit:
            https://bugzilla.readthedocs.io/en/5.0/api/core/v1/bug.html
    '''

    def __init__(self, url_base, token):
        super(BugzillaWebService, self).__init__(url_base, token)

    def Get_Bug(self, id_alias=None, include_fields=None):
        return bugs.Get_Bug(self.url_base, self.token, id_alias, include_fields)

    def Bug_History(self, bug_id, new_since=None):
        return bugs.Bug_History(bug_id, self.url_base, self.token, new_since)

    def Search_Bugs(self, *args, **kwargs):
        return bugs.Search_Bugs(self.url_base, self.token, *args, **kwargs)

    def Search_Bugs(self, *args, **kwargs):
        return bugs.Search_Bugs(self.url_base, self.token, *args, **kwargs)


if __name__ == '__main__':
    a = BugzillaWebService(url_base="https://bz.labs.company.com", token="3546-t2iKyULbjn")
    res = a.Search_Bugs(product=["BMC", 'BIOS', 'CMM', 'CMM_BLUE', 'EMS', 'IMM2', 'IMM2_BLUE', 'IMM3', 'LXPM', 'LXPM4',
                  'PSOC', 'SEP', 'SMM', 'SMM2', 'TMM', 'Translation', 'TSM', 'uEFI', 'UEFI2', 'UEFI3', 'UEFI3_BLUE',
                  'UEFI4', 'UEFI5', 'UEFI6', 'Z_AMI', 'z_Avocent_SW', 'z_Compal_FW', 'z_Emerson_SW', 'z_IEC_FW',
                  'z_Pegatron_SW', 'z_USI_FW', 'z_Wistron_SW', 'Broadcom', 'Intel_Network', 'RHEL', 'CentOS',
                  'System_ECAT', 'z_USI_HW', 'LXCE_OneCLI', 'FPGA', 'LSI_RAID'],
        creation_time="2022-04-01", summary=["qtester","Qtester"])
    print(res[1]['bugs'])
    # a = ['Genoa', 'EGS', 'Hakuba']
    # for i in a:
    #     n = 0
    #     for j in range(len(res[1]['bugs'])):
    #         if i in res[1]['bugs'][j]['summary'] or str.lower(i) in res[1]['bugs'][j]['summary']:
    #             n += 1
    #     ret[i] = n
    # print(ret)
    print(len(res[1]["bugs"]))

# creator=["gujie5@company.com", "hanmw1@company.com", "huangyj31@company.com", "niuzhen2@company.com",
#                  "renjl8@company.com", "liyang118@company.com", "huangsk3@company.com", "chendw5@company.com",
#                  ]
