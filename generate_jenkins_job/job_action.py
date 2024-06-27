import json

import jenkins
import logging

from pathlib import Path
from subprocess import getstatusoutput
# from fastapi import HTTPException

from generate_jenkins_job.jenkins_config import JenkinsConfig

JENKINS_URL = JenkinsConfig.URL
JENKINS_USER = JenkinsConfig.USER
JENKINS_PWD = JenkinsConfig.PWD
TEMPLATE = Path.cwd().joinpath("generate_jenkins_job/template/template.json")
JOB_DATA = Path.cwd().joinpath('generate_jenkins_job/job_data')
JOB_CONFIG = Path.cwd().joinpath("generate_jenkins_job/template/job_config.json")

folder_config = [
    {
        "job": {
            "name": "",
            "project-type": "folder"
        }

    }
]

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S'
                    )


class JobAction:
    __obj = None

    def __new__(cls, *args, **kwargs):
        if cls.__obj is None:
            cls.__obj = object.__new__(cls)
        return cls.__obj

    def __init__(self, *args, **kwargs):
        self.category = kwargs.get("category")
        self.name = kwargs.get("name")
        self.immip = kwargs.get("immip")
        self.config = kwargs.get("config")
        self.tag = kwargs.get("tag")

        self.origin_category = kwargs.get("origin_category")
        self.origin_name = kwargs.get("origin_name")
        self.origin_immip = kwargs.get("origin_immip")
        self.origin_config = kwargs.get("origin_config")
        if self.origin_config:
            self.origin_config = self.origin_config["jenkins_config"]
            self.test_type_list = list(self.origin_config.keys())
        if self.config:
            self.config = self.config["jenkins_config"]
            self.test_type_list = list(self.config.keys())

        self.jenkins_server = jenkins.Jenkins(
            JENKINS_URL)
        if JOB_DATA.is_dir():
            for file in JOB_DATA.iterdir():
                file.unlink()
            JOB_DATA.rmdir()
        JOB_DATA.mkdir()

        action = kwargs.get("action")
        logging.info(action)
        if self.config:
            logging.info("config:")
            logging.info(self.config)

        if self.origin_config:
            logging.info("origin config:")
            logging.info(self.origin_config)

    def create_job(self):
        if len(self.test_type_list) == 0:
            return False
        # job template render
        for test_type in self.test_type_list:
            dict_data = dict
            with open(TEMPLATE, 'r') as f_template:
                dict_data = json.load(f_template)
                dict_data[0]["job"][
                    "name"] = f"{test_type}{self.category}/{test_type}_{self.category}_{self.name}_{self.immip}"
                dict_data[0]["job"]["parameters"][0]["choice"]["choices"][0] = self.immip
                dict_data[0]["job"]["parameters"][1]["choice"]["choices"][0] = self.category

                for test_function in self.config[test_type]:
                    for test_item in self.config[test_type][test_function]:
                        temp_test_item = {
                            "string": {
                                "default": "0",
                                "name": "",
                                "trim": "false"
                            }
                        }
                        if test_function == "xcc_test":
                            temp_test_item["string"]["name"] = f"{test_item}_XTEST"
                        elif test_function == "uefi_test":
                            temp_test_item["string"]["name"] = f"{test_item}_UTEST"
                        elif test_function == "stress_test":
                            temp_test_item["string"]["name"] = f"{test_item}_STEST"
                        elif test_function == "performance_test":
                            temp_test_item["string"]["name"] = f"{test_item}_PTEST"
                        elif test_function == "memory_test":
                            temp_test_item["string"]["name"] = f"{test_item}_MTEST"
                        dict_data[0]["job"]["parameters"].append(temp_test_item)
                temp_param = [
                    {
                        "string": {
                            "default": "1",
                            "name": "LOOP",
                            "trim": "false"
                        }
                    },
                    {
                        "bool": {
                            "default": 'false',
                            "name": "BUILD_DOCKER"
                        }
                    },
                    {
                        "bool": {
                            "default": 'false',
                            "name": "DRAFT"
                        }
                    },
                    {
                        "string": {
                            "default": "",
                            "name": "SENDER",
                            "trim": "false"
                        }
                    },
                    {
                        "string": {
                            "default": "",
                            "name": "RECEIVER",
                            "trim": "false"
                        }
                    }
                ]
                dict_data[0]["job"]["parameters"] += temp_param
                temp_hour = {
                    "string": {
                        "default": "1",
                        "name": "TimeOut",
                        "trim": "false"
                    }
                }
                if test_type == "memorystress":
                    dict_data[0]["job"]["parameters"].append(temp_hour)
                with open(JOB_CONFIG, 'r') as config_f:
                    config_data = json.load(config_f)[self.tag][test_type]
                    for key in config_data['top']:
                        if key.startswith("env"):
                            dict_data[0]["job"]["dsl"] += f"{key} = {config_data['top'][key]}\n"
                        else:
                            dict_data[0]["job"]["dsl"] += f"{config_data['top'][key]}\n"
                    dict_data[0]["job"]["dsl"] += " \n"
                    for test_function in self.config[test_type]:
                        for test_item in self.config[test_type][test_function]:
                            dict_data[0]["job"][
                                "dsl"] += f"env.{test_item} = '{self.config[test_type][test_function][test_item]}'\n"
                    dict_data[0]["job"]["dsl"] += "\n"
                    dict_data[0]["job"]["dsl"] += f"env.TEST_TYPE = '{test_type}'\n"
                    dict_data[0]["job"]["dsl"] += f"env.TITLE = '{self.category}'\n"
                    dict_data[0]["job"]["dsl"] += "\n"
                    for key in config_data['bottom']:
                        if key.startswith("env"):
                            dict_data[0]["job"]["dsl"] += f"{key} = {config_data['bottom'][key]}\n"
                        else:
                            dict_data[0]["job"]["dsl"] += f"{config_data['bottom'][key]}\n"
            # generate config file
            target_json = JOB_DATA.joinpath(f"{test_type}_{self.category}_{self.name}_{self.immip}.json")
            with open(target_json, 'w') as f_target:
                f_target.write(json.dumps(dict_data, indent=4))

            # check folder
            self.check_jenkins_folder(test_type, f"{test_type}{self.category}")

        # build job
        for data in JOB_DATA.iterdir():
            self.jenkins_build("update", data)
        return True

    def update_job(self):
        try:
            if (self.category != self.origin_category) or (self.name != self.origin_name) or (
                    self.immip != self.origin_immip) or (self.config != self.origin_config):
                if self.delete_job():
                    return self.create_job()
            else:
                logging.info("All of host settings is same as previous, so no need modify.")
                return True
        except Exception as e:
            logging.error(e)
            return False

    def delete_job(self):
        try:
            test_type_list = list(self.origin_config.keys()) if self.origin_config else self.test_type_list
            for test_type in test_type_list:
                target_job = f"{test_type}{self.origin_category}/{test_type}_{self.origin_category}_{self.origin_name}_{self.origin_immip}"
                if self.jenkins_server.get_job_name(target_job) is not None:
                    self.jenkins_build("delete", target_job)
                    try:
                        folder_info = self.jenkins_server.get_job_info(
                            f"{test_type}{self.origin_category}")
                        if len(folder_info['jobs']) == 0:
                            self.jenkins_build(
                                "delete", f"{test_type}{self.origin_category}")
                    except jenkins.JenkinsException:
                        pass
                else:
                    logging.info(f"no {test_type} job in jenkins")
            return True
        except Exception as e:
            logging.error(e)
            return False

    def jenkins_build(self, action, action_obj):
        cmd = f"jenkins-jobs {action} {action_obj}"
        status, output = getstatusoutput(cmd)
        if status != 0:
            print(output)
            raise Exception

    def check_jenkins_folder(self, view, folder):
        try:
            self.jenkins_server.is_folder(folder)
        except jenkins.JenkinsException:
            self.create_folder(folder)
            view_xml = self.jenkins_server.get_view_config(view)
            view_xml = view_xml.replace(
                "</jobNames>", "  <string>" + folder + "</string>" + "\n  </jobNames>")
            self.jenkins_server.reconfig_view(view, view_xml)

    def create_folder(self, name):
        folder_config[0]["job"]["name"] = name
        with open(f'{name}.json', 'w') as f:
            f.write(str(folder_config))
        self.jenkins_build("update", f"{name}.json")

    def __del__(self):
        test_type_list = list(self.origin_config.keys()) if self.origin_config else self.test_type_list
        for test_type in test_type_list:
            Path(f"{test_type}_{self.origin_category}_{self.origin_name}_{self.origin_immip}.json").unlink()
            if Path(f"{test_type}{self.category}.json").exists():
                Path(f"{test_type}{self.category}.json").unlink()
