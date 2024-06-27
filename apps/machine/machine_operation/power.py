# -*- coding: utf-8 -*-
"""
@Time ： 5/12/23 5:57 PM
@Auth ： gujie5
"""

import paramiko
import requests
import json
from webportal import settings
import logging
import logging.handlers
import traceback
import pexpect
import time
from subprocess import getstatusoutput

power_url = '/redfish/v1/Systems/1/Actions/ComputerSystem.Reset/'
status_url = '/redfish/v1/Systems/1/'


def system_power(baseUrl, username, password, action):
    url = f"https://{baseUrl}{power_url}"
    header = {"Content-type": "application/json"}
    data = {"ResetType": "ForceOn"} if action == "on" else {"ResetType": "ForceOff"}
    resp = requests.post(url=url, data=json.dumps(data), headers=header, auth=(username, password),
                         verify=False).status_code
    if "20" in str(resp):
        return True
    else:
        return False


def get_ssh(ip, user, passwd, port=22, retry=3, retry_interval=10):
    # if retry < 0:
    #     raise Exception("SSH connect %s failed. No More Retry! Throw Error!" % (ip))
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    for i in range(retry):
        ssh_success = True
        try:
            ssh.connect(
                ip,
                port,
                user,
                passwd,
                banner_timeout=30,
                auth_timeout=30,
                allow_agent=False,
            )
        except:
            time.sleep(retry_interval)
            ssh_success = False
        if i < retry and ssh_success:
            print("SSH connect %s Success" % (ip))
            break
        elif i == retry - 1 and not ssh_success:
            raise Exception("SSH connect %s failed. No More Retry! Throw Error!" % (ip))
        logging.warning("SSH connect %s failed, retry connect times: %s" % (ip, i + 1))
    return ssh


def processCommand(session, userCommand, expectList, retries=2):
    i = 0
    while i < retries:
        i += 1
        print('Send ---> %s ' % userCommand)
        session.sendline(userCommand)
        time.sleep(0.1)
        idx = session.expect(expectList, timeout=100)
        if idx == 0:
            print('Pass ---> %s ' % userCommand)
            return True, session.before
    return False, None


def get_key(immip, immuser, immpasswd):
    """
    First get key from host by CLI command "dbgshimm"
    """
    global sshSes
    result = []

    ip = immip
    user = immuser
    password = immpasswd
    getstatusoutput("rm -rf ~/.ssh/known_hosts")
    try:
        sshSes = pexpect.spawn('bash', timeout=60)
        # sshSes.logfile = sys.stdout

        print(' Logging in %s ' % ip)
        sshSes.sendline("ssh -l %s %s" % (user, ip))
        ret = sshSes.expect(['[P|p]assword', 'Are you sure you want to continue connecting (yes/no)?'])
        if ret == 0:
            processCommand(sshSes, password, ['system>'], 2)
        elif ret == 1:
            processCommand(sshSes, 'yes', ['[P|p]assword'], 1)
            processCommand(sshSes, password, ['system>'], 2)
        result = processCommand(sshSes, 'dbgshimm', ['Please input response message, followed by Ctrl-D:'], 2)
        # sshSes.sendcontrol('d')
        # sshSes.expect('system>')

        i = 0
        while i < 2:
            i += 1
            sshSes.sendcontrol('d')
            idx = sshSes.expect('system>', timeout=60)
            if idx == 0:
                sshSes.sendline('exit')
                break
    except Exception as e:
        traceback.print_exc()
        print('==> Fail login %s' % ip)
        raise Exception('==> Fail login %s' % ip)
    if result[0]:
        _key = result[1].decode().strip()
        key = _key.strip("dbgshimm").strip()
        return key


def get_response_key(key, backdoor_type):
    global sshServer
    result = ''
    backdoorServer = settings.BACKDOOR_SERVER
    ip = backdoorServer.get('ip')
    user = backdoorServer.get('user')
    password = backdoorServer.get('password')

    try:
        sshServer = pexpect.spawn('bash', timeout=20)
        # sshServer.logfile = sys.stdout

        print(' Logging in %s ' % ip)
        sshServer.sendline("ssh -l %s %s" % (user, ip))
        ret = sshServer.expect(['[P|p]assword', 'Are you sure you want to continue connecting (yes/no)?'])
        # print ret
        if ret == 0:
            processCommand(sshServer, password, ['\$'], 2)
        elif ret == 1:
            processCommand(sshServer, 'yes', ['[P|p]assword'], 2)
            processCommand(sshServer, password, ['\$'], 2)
        processCommand(sshServer, 'imm3env', ['\$'], 2)
        processCommand(sshServer, backdoor_type, ['enter a single Control-D'], 2)

        i = 0
        while i < 2:
            i += 1
            sshServer.sendline(key)
            sshServer.sendcontrol('d')
            idx = sshServer.expect('FAKEROOT', timeout=60)
            if idx == 0:
                result = sshServer.before
                print(result)
                break
    except Exception as e:
        traceback.print_exc()
        print(e)
        print('==> Fail login test ')
    if result:
        result = result.decode()
        _resp = result.strip().split('---\r\n')[-1].split('\r\n\r\n')[1].rstrip()
        return _resp
    else:
        print("==> get response fail")


def get_cli_response(imm_ip, imm_user, imm_passwd, cmd, wait=0.1):
    print(cmd)
    output = ""
    try:
        with get_ssh(imm_ip, imm_user, imm_passwd, retry=6) as ssh:
            stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True, timeout=5)
            output = stdout.read().decode()
            time.sleep(wait)
        if not output:
            print("stdout is null,and next is stderr content:")
            print(stderr.read())
        return output
    except Exception as e:
        print(e)
        return output


def open_backdoor(immip, immuser, immpasswd, response):
    """
    Just use response to open back door if status is "Secure debug ports are NOT open"
    """
    backdoor_status = get_cli_response(immip, immuser, immpasswd, 'dbgshimm status')
    print("backdoor status:")
    print(backdoor_status)
    if "NOT open" in backdoor_status:
        print("Backdoor is not open, will open it...")
        return open_backdoor_run(immip, immuser, immpasswd, response)


def open_backdoor_run(immip, immuser, immpasswd, response):
    """
    Send the key by CLI command
    response: the key which get from sign server.
    """
    global sshSes
    result = []

    ip = immip
    user = immuser
    password = immpasswd

    try:
        sshSes = pexpect.spawn('bash', timeout=150)
        # sshSes.logfile = sys.stdout

        print(' Logging in %s ' % ip)
        sshSes.sendline("ssh -l %s %s" % (user, ip))
        time.sleep(2)
        ret = sshSes.expect(['[P|p]asswor[d|d:]', 'Are you sure you want to continue connecting (yes/no)?'])
        print(ret)
        if ret == 0:
            print(processCommand(sshSes, password, ['system>'], 2))
        elif ret == 1:
            print(processCommand(sshSes, 'yes', ['[P|p]assword[d|d:]'], 1))
            print(processCommand(sshSes, password, ['system>'], 2))
        print("start to send command : dbgshimm")
        processCommand(sshSes, 'dbgshimm', ['Please input response message, followed by Ctrl-D:'], 2)
        i = 0
        while i < 2:
            i += 1
            sshSes.sendline(response)
            sshSes.sendcontrol('d')
            idx = sshSes.expect(['system>', 'Signature verification failed'], timeout=60)
            if idx == 0:
                break
            if idx == 1:
                print('==> Singnature  fail')
                break
    except Exception as e:
        traceback.print_exc()
        print(e)
        try:
            print(sshSes.before)
        except:
            try:
                print(sshSes.readlines())
            except:
                pass
            pass
        print('==> Fail login test ')
    print("check dbgshimm status")
    result = processCommand(sshSes, 'dbgshimm status', ['system>'], 2)
    if result[0] and "hrs remaining" in result[1].decode():
        print("Open backdoor success, use 'ssh -p 122 immdebug@IPADDR' to access the debug shell")

        sshSes.sendline('exit')
        return True
    else:
        print("Open backdoor fail.")
        sshSes.sendline('exit')
        return False


class XCCBackdoor(object):
    '''
    1. open the xcc backdoor, the port is 122
        * ssh to xcc cli and then run 'dbgshimm' to get a key.
        * login to build server
        * run 'mcpenv & debug_sign'
        * input that key from step 1, it will get a response.
        * imput a response to xcc cli. it will open the xcc backdoor.
    2. run the cmd to get mem and cpu info
    '''

    def __init__(self, imm_ip, imm_user="USERID", imm_passwd="PASSW0RD"):
        self.imm_ip = imm_ip
        self.imm_user = imm_user
        self.imm_passwd = imm_passwd

    def open_back_door(self, **args):
        """
        For first open back door
        """
        # 1. get key from host
        key = get_key(self.imm_ip, self.imm_user, self.imm_passwd)
        if 'expires' in key:
            key = key.split('\r\n', 1)[-1]
        # 2. use the key to get response from backdoor server
        # get open backdoor args from apollo
        backdoor_type = args.get('backdoorconfig', "debug_sign_4k384")
        response = get_response_key(key, backdoor_type)
        print("server response is:")
        print(response)
        # 3. use the response to sign the host
        return open_backdoor(self.imm_ip, self.imm_user, self.imm_passwd, response)
        pass

    def openbackdoor(self, **args):
        """
        For first and reopen back door
        Use CLI command to check the backdoor status
        1. Login to CLI
        2. Execute command and show CLI logs: 'dbgshimm status'
        * 'Secure debug ports are NOT open': backdoor is not open
        * 'Secure debug ports are open: 23 hrs remaining': need reopen the backdoor after * hours,
            but before reopen it, you need disable it first by CLI command "dbgshimm disable"
        """
        try:
            immip = self.imm_ip
            immuser = self.imm_user
            immpasswd = self.imm_passwd
            backdoor_status = get_cli_response(immip, immuser, immpasswd, 'dbgshimm status')
            print("backdoor status:")
            print(backdoor_status)
            if "Secure debug ports are NOT open" in backdoor_status:
                return self.open_back_door(**args)
            if "Secure debug ports are NOT open" not in backdoor_status:
                remain_hour = backdoor_status.replace(' ', '')[
                              backdoor_status.replace(' ', '').find(':') + 1:backdoor_status.replace(' ', '').find(
                                  'hrs')]
                if int(remain_hour) <= 5:
                    print("the remain hour is less than 5 hours reopen backdoor")
                    backdoor_status = get_cli_response(immip, immuser, immpasswd, 'dbgshimm disable', 1)
                    print("Disable backdoor first, and then reopen it to renew the backdoor expired time...")
                    print(backdoor_status)
                    if 'ok' in backdoor_status:
                        print('disable backdoor success! And then reopen it')
                        return self.open_back_door(**args)
                    else:
                        print('disable the backdoor fail')
                        time.sleep(10)
                        self.openbackdoor(**args)
                else:
                    print("the remain hours more than 5 hours")
            return True
        except Exception as e:
            print(e)
            return False


if __name__ == '__main__':
    backdoor = XCCBackdoor("10.240.216.118", "USERID", "FW2020bbfv")
    backdoor.openbackdoor()
