# -*- coding: utf-8 -*-
"""
@Time ： 4/25/23 2:49 PM
@Auth ： gujie5
"""
from webportal import settings
from generate_jenkins_job.job_action import JobAction

jenkins_job_url = settings.JENKINS_JOB_URL


def check_config_message(config, tag):
    if config.get('jenkins_config'):
        if tag == 'auto':
            config.get('jenkins_config').pop("mrt", None)
        else:
            for i in ['xpit', 'performance', 'memorystress', 'daily']:
                config.get('jenkins_config').pop(i, None)
    return config


def create_job(category, name, immip, config: dict, tag):
    if tag == "develop" or tag == "auto":
        config = check_config_message(config, tag)
        data = {"category": category, "name": name, "immip": immip, "action": "create", "config": config, "tag": tag}
        job_handle = JobAction(
            **data)
        if job_handle.create_job():
            return True
        else:
            return False
    else:
        return True


def update_job(origin_category, origin_name, origin_immip, category, name, immip, config: dict, origin_config: dict,
               tag, origin_tag):
    if tag == "develop" or tag == "auto":
        config = check_config_message(config, tag)
        origin_config = check_config_message(origin_config, origin_tag)
        if origin_category != category or origin_name != name or origin_immip != immip or config.get(
                "jenkins_config") != origin_config.get("jenkins_config"):
            data = {"origin_category": origin_category, 'origin_name': origin_name, "origin_immip": origin_immip,
                    "category": category, "name": name, "immip": immip, "action": "update",
                    "origin_config": origin_config,
                    "config": config, "tag": tag}
            job_handle = JobAction(
                **data)
            if job_handle.update_job():
                return True
            else:
                return False
        else:
            return True
    else:
        return True


def delete_job(origin_category, origin_name, origin_immip, config, tag):
    if tag == "develop" or tag == "auto":
        data = {"origin_category": origin_category, 'origin_name': origin_name, "origin_immip": origin_immip,
                "config": config, "tag": tag, "action": "delete"}
        job_handle = JobAction(**data)
        if job_handle.delete_job():
            return True
        else:
            return False
    else:
        return True
