# -*- coding: utf-8 -*-
"""
@Time ： 1/13/23 4:00 PM
@Auth ： gujie5
"""
# -*- coding: utf-8 -*-

import jenkins
import time
from webportal import settings as config
import logging


def getServer():
    """
    return jenkins server handler
    Our jenkins server don't use token
    """
    AUTH = ()
    server = JenkinsServer(config.JENKINS_URL, *AUTH, timeout=10)
    if not server:
        logging.error("Jenkins server is down or not found, please check")
    return server


class JenkinsServer(jenkins.Jenkins):

    def __init__(self, *args, **kwargs):
        super(JenkinsServer, self).__init__(*args, **kwargs)

    def buildJob(self, name, parameters=None, token=None):
        """
        return ret (int, string)
            fail ret = 0;
            Not Buildable or in Queue ret = -1;
            success ret > 0;
        """
        try:
            job_info = self.get_job_info(name)
        except jenkins.NotFoundException as e:
            logging.error("------------%s" % e.message)
            return -3, e.message
        nextBuildNumber = job_info['nextBuildNumber']
        # lastCompletedBuildNumber = 0
        # if job_info["lastCompletedBuild"]:
        #     lastCompletedBuildNumber=job_info["lastCompletedBuild"]["number"]
        # if nextBuildNumber != lastCompletedBuildNumber+1:
        #     return -1, "Last Build not Completed."
        if job_info["inQueue"]:
            logging.info("------------%s" % job_info)
            return -1, "Job in Queue"
        try:
            self.build_job(name, parameters, token)
        except jenkins.NotFoundException as e:
            logging.error("------------%s" % e.message)
            return -3, e.message
        else:
            success = False
            trycount = 0
            while not success and trycount < 10:
                try:
                    trycount += 1
                    self.get_build_info(name, nextBuildNumber)
                except Exception as e:
                    time.sleep(1)
                else:
                    success = True
        return nextBuildNumber, "ok"


if __name__ == '__main__':
    server = getServer()
    buildInfo = server.get_job_name('performanceFWAgile/performance_FWAgile_Colossus_10.240.216.118')
    jobname = "Performance23A/performance_23A_Cable"
    # buildInfo = server.get_job_info(jobname)
    print(buildInfo)
    import json

    # print(json.dumps(buildInfo))
