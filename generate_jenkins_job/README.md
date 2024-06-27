# Automation manage Jenkins job


## Environment setup

### Base environment

1. Linux
1. Python3.8+


### Configuratin file

1. create jenkins_jobs.ini configuration file

file path: /etc/jenkins_jobs/jenkins_jobs.ini
```
[job_builder]
ignore_cache=True
keep_descriptions=False
include_path=.:scripts:~/git/
recursive=False
exclude=.*:manual:./development
allow_duplicates=False
update=all

[jenkins]
user=$jenkins_username
password=$jenkins_passwd
url=http://$jenkins_address:$port/
query_plugins_info=False
##### This is deprecated, use job_builder section instead
#ignore_cache=True

[plugin "hipchat"]
authtoken=dummy

[plugin "stash"]
username=$jenkins_username
password=$jenkins_passwd
```
2. change jenkins_config.py  
```
    URL = "http://$jenkins_address:$port/"  
    USER = "$jenkins_username"  
    PWD = "$jenkins_passwd"
```

## Usage

Action:  
* API: http://{server_ip}:8001
1. create
```
request data:
{
  "category": {category},
  "name": {name},
  "immip": {immip},
  "action": "create",
  "config": {
    "test_config":{},
    "jenkins_config":{}
  }
}

Note:
{category} -> target host category
{name} -> target host name
{immip} -> target host immip
config -> target host config
```
2. update
```
request data:
{
  "origin_category": {origin_category},
  "origin_name": {origin_name},
  "origin_immip": {origin_immip},
  "origin_config": {
    "test_config":{},
    "jenkins_config":{}
  }
  "category": {category},
  "name": {name},
  "immip": {immip},
  "action": "update",
  "config": {
    "test_config":{},
    "jenkins_config":{}
  }
}

Note:
{category} -> new host category
{name} -> new host name
{immip} -> new host immip
config -> new host config

{origin_category} -> old host category
{origin_name} -> old host name
{origin_immip} -> old host immip
origin_config -> old host config
```
3. delete
```
request data:
{
  "origin_category": {origin_category},
  "origin_name": {origin_name},
  "origin_immip": {origin_immip},
  "origin_config": {
    "test_config":{},
    "jenkins_config":{}
  }
}

Note:
{origin_category} -> target host category
{origin_name} -> target host name
{origin_immip} -> target host immip
origin_config -> old host config

```
## jenkins_config template
```
{
    "config": {
        "test_config": {},
        "jenkins_config": {
            "mrt": {
                "xcc_test": {
                    "flashXCC": "",
                    "flashUEFI": "",
                    "miscXCC": "",
                    "redfishProtocol": "",
                    "redfishService": "",
                    "security": "",
                    "checkFFDC": ""
                },
                "uefi_test": {
                    "bootManager": "",
                    "powerProcessor": ""
                },
                "stress_test": {
                    "flashXCCStress": "",
                    "flashUEFIStress": "",
                    "flashXCCupdownStress": "",
                    "flashUEFIupdownStress": "",
                    "flashXCCupdownLXCAStress": "",
                    "flashUEFIupdownLXCAStress": "",
                    "ACStress": "",
                    "DCStress": "",
                    "bmcRestartStress": "",
                    "warmRebootStress": "",
                    "miscStress": ""
                }
            }
        }
    }
}
```