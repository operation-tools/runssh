#!/usr/bin/python2.7
#coding=utf-8

import os
import sys
import re
import json
import pexpect
import argparse
from jsonpath import jsonpath
from collections import OrderedDict

class Check():
    # 初始化配置文件，并创建对应的目录
    def init_cfg_file(self, config_file, init_cfg_data=''):
        cfg_path = os.path.dirname(config_file)
        os.path.isdir(cfg_path) if os.path.isdir(cfg_path) else os.makedirs(cfg_path)
        if not os.path.isfile(config_file):
            with open(config_file, 'w') as f:
                f.write(init_cfg_data)

    # int() 范围校验
    def int_range(self, num, start_point=1, end_point=65535, hint=''):
        try:
            if int(num) not in range(start_point, end_point):
                return "ERROR: %s %s more than the scope of, range out of: %s ~ %s ." % (hint, num, start_point, end_point)
        except (ValueError) as e:
            print e
            return "ERROR: %s expect type: int, input type: %s " % (hint, type(num))
        except Exception as e:
            print e
            return "ERROR: %s happen an unknown error in int_range()."

    # 开关校验
    def switch(self, switch, hint=''):
        try:
            if int(switch) not in [0, 1]:
                return "ERROR: %s only support 0 or 1, you input value: %s" % (hint, switch)
        except (ValueError) as e:
            print e
            return "ERROR: %s expect type: int, input type: %s " % (hint, type(switch))
        except Exception as e:
            print e
            return "ERROR: %s happen an unknown error in switch()."

    # NAME字段校验，无特殊字符，不能以数字-_开头，不能以-_结尾的命名
    # 不合格例子如：_host 89host host2- h&sd
    # 合格例子：my_host1
    def name(self, string, hint=''):
        try:
            reg = '^[a-zA-Z][\w-]+[a-zA-Z0-9]$'
            if not re.match(reg, string.strip()):
                return "ERROR: field format error. expect: %s , input: %s  \n\t %s" % (reg, string, hint)
        except Exception as e:
            print e
            return "ERROR: happen an unknown error in ck_name()."

    # 文件存不存在
    def _isfile(self, file, default_dir, hint=''):
        try:
            r = re.match('^/.*', file.strip())
            if not r:
                file = '%s/%s' % (default_dir, file)
            if not os.path.isfile(file):
                return "ERROR: %s %s file not found." % (file, hint)
        except Exception as e:
            print e
            return "ERROR: happen an unknown error in _isfile()."

    # host 支持 IP 和 Domain
    def host(self, host, hint=''):
        try:
            l = host.split('.')
            c = 0
            for i in l:
                if i.isalnum():
                    c = c + 1
            if c == len(l):
                reg = '(\d{1,3}\.){3}\d{1,3}$'
            else:
                reg = '^(?=^.{3,255}$)[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})+[a-zA-Z0-9]$'

            if not re.match(reg, host.strip()):
                return "ERROR: %s Only IP and domain name formats are supported. input: %s" % (hint, host)
        except Exception as e:
            print e
            return "ERROR: happen an unknown error in host()."



class CredentialOptions():
    def __init__(self, credential_file, reg_remove=''):
        self.credential_file = credential_file
        self.reg_rm = reg_remove
    # 读取凭证文件，返回列表或json数据
    def read(self, type_localtion=(999, "A类0", "B类1"), dict_fields=[]):
        # 文件中不想要的行，例子文本内容如下：
        '''
        NAME   HOST   PORT  USER  PASS   KEY    JUMP  DESC
        [Normal Server]
        my_host1  192.168.1.20  22  root  123456  None    0  测试机（用密码登陆的）
        my_jump  192.168.1.162  22  root  None  key_file    0  跳板机（用密钥登陆）

        [Need Jump Server]
        my_host2  192.168.2.100  22  root  789123  None    1  需要跳板机才能登陆的测试机（用密码登陆）
        '''
        '''
        reg_remove参数：
                不加此参数表示不启用；
                如果我不想要 NAME... 、 [Normal Server] 、 [Need Jump Server] 这三行，可这样配置reg_remove='^NAME.*|^\[.*'
        
        type_localtion参数 和 dict_fields=[]参数：
                不加这两个参数，会返回一个列表，启用dict_fields参数的时候，type_localtion参数才有效；
                使用dict_fields=[]，会返回一个json数据，上文中my_host1行中有8个字段（空白符隔开），
                    还有一个隐藏字段，文件行号，所以一共是9个字段，我们可以传递类似以下的字段，以下字段就是json的Key值：
                    dict_fields=['line', 'name', 'host', 'port', 'username', 'password', 'privateKey', 'jumpTag', 'describe']
                    得到的结果就像这样：
                    {
                        "Content": [{
                            "line": "3",
                            "name": "my_host1",
                            "host": "192.168.1.161",
                            "port": "22",
                            "username": "root",
                            "password": "123456",
                            "privateKey": "None",
                            "jumpTag": "0",
                            "describe": "测试机（用密码登陆的）"
                        }, {
                            "line": "4",
                            "name": "my_jump",
                            "host": "192.168.1.162",
                            "port": "22",
                            "username": "root",
                            "password": "None",
                            "privateKey": "key_file",
                            "jumpTag": "0",
                            "describe": "跳板机（用密钥登陆）"
                        }]
                    }
                使用type_localtion参数，将json数据根据某个字段分割成两组json数据，该字段就像一个开关（必须为0或1，比如上面的JUMP字段），
                    由于我们将这个字段定义为jumpTag，所以我们可以这样赋值：  # 分别是 标示字段，字段值为0的组名，字段值为1的组名
                    type_localtion=('jumpTag', 'normalServer', 'needJumpServer')  
                    得到的结果就像这样：
                    {
                        "normalServer": [{
                            "line": "3",
                            "name": "my_host1",
                            "host": "192.168.1.161",
                            "port": "22",
                            "username": "root",
                            "password": "123456",
                            "privateKey": "None",
                            "jumpTag": "0",
                            "describe": "测试机（用密码登陆的）"
                        }, {
                            "line": "4",
                            "name": "my_jump",
                            "host": "192.168.1.162",
                            "port": "22",
                            "username": "root",
                            "password": "None",
                            "privateKey": "key_file",
                            "jumpTag": "0",
                            "describe": "跳板机（用密钥登陆）"
                        }],
                        "needJumpServer": [{
                            "line": "7",
                            "name": "my_host2",
                            "host": "192.168.2.100",
                            "port": "22",
                            "username": "root",
                            "password": "789123",
                            "privateKey": "None",
                            "jumpTag": "1",
                            "describe": "需要跳板机才能登陆的测试机（用密码登陆）"
                        }]
                    }
        '''
        _list = []
        r_list = []
        a_list = []
        b_list = []
        j = OrderedDict()
        try:
            cpatt = re.compile(self.reg_rm)
            with open(self.credential_file) as f:
                for line_num, data in enumerate(f, 1):
                    if self.reg_rm:
                        _data = cpatt.sub('\n', data)
                    if re.search('^\s+$', _data):
                        continue
                    if not _data:
                        break
                    _list.append('%s %s' % (str(line_num), _data))
                if dict_fields:
                    if type_localtion[0] == 999:
                        for i in _list:
                            _j = OrderedDict(zip(dict_fields, i.split()))
                            r_list.append(_j)
                            j.update({"Content": r_list})
                        return json.dumps(j, ensure_ascii=False)
                    else:
                        for i in _list:
                            _j = OrderedDict(zip(dict_fields, i.split()))
                            _type = jsonpath(_j, '$..%s' % type_localtion[0])
                            _type = int(_type[0])
                            if _type == 0:
                                a_list.append(_j)
                                j.update({type_localtion[1]: a_list})
                            elif _type == 1:
                                b_list.append(_j)
                                j.update({type_localtion[2]: b_list})
                        return json.dumps(j, ensure_ascii=False)
            return _list
        except (Exception) as e:
            return "ERROR: %s" % e

    # 搜索凭证
    def search(self, req, type="normal"):
        sshconf = CredentialOptions(self.credential_file, reg_remove='^NAME.*|^\[.*')
        content = sshconf.read(
            type_localtion=('jumpTag', 'normalServer', 'needJumpServer'),
            dict_fields=['line', 'name', 'host', 'port', 'username', 'password', 'privateKey', 'jumpTag',
                         'describe'])
        # print content

        j = {}
        l = []
        if type != "normal":
            data = jsonpath(json.loads(content), expr='$..needJumpServer')[0]
        data = jsonpath(json.loads(content), expr='$..normalServer')[0]
        for d in data:
            name = jsonpath(d, expr='$..name')[0]
            host = jsonpath(d, expr='$..host')[0]
            _name_re = re.match(req, name)
            _host_re = re.match(req, host)
            if _name_re:
                l.append(d)

        j.update({"%s" % type: l})
        return json.dumps(j, ensure_ascii=False)


# 打印错误提示：
class Output():
    # 格式错误
    def format_error(self):
        print 'ERROR: Format error, please use %s --help to see how to use it.' % sys.argv[0]
        exit(400)
    # 选项错误
    def invalid_option(self, option):
        print "ERROR: Invalid option %s , please use %s --help to see how to use it." % (option, sys.argv[0])
        exit(400)
    # 不存在
    def not_found(self, hint=''):
        print "ERROR: The information could not be found. %s" % (hint)
        exit(400)

class Command():
    def __init__(self, username, host, port, password, private_key, timeout=10, debug_switch=1):
        # 必要的参数
        self.username = username
        self.host = host
        self.port = port
        self.password = password
        self.private_key = private_key
        # 其他参数
        self.timeout = timeout
        self.debug_switch = debug_switch

    def pexpect_passwd(self, cmd, remote_cmd=None, jump_password=None):
    # cmd参数表示能够直接登陆的服务器命令（[NormalServer]列表下），remote_cmd参数表示通过jumper服务器才能登陆的命令（[NeedJumpServer]列表下）
        try:
            ssh = pexpect.spawn(cmd, timeout=self.timeout)  # logfile=sys.stdout
            # choose = ssh.expect(['continue connecting (yes/no)?', 'password:'], timeout=self.timeout)
            # if choose == 0:
            # ssh.sendline('yes')
            # ... ...
            # elif choose == 1:
            # ... ...
            ssh.expect('password:', timeout=self.timeout)
            if jump_password:
                ssh.sendline(jump_password)
            else:
                ssh.sendline(self.password)

            # 跳板机
            if remote_cmd:
                user_type = ssh.expect([']#', ']$'], timeout=self.timeout)
                if user_type in (0, 1):
                    ssh.sendline(remote_cmd)
                    if re.search('\s-i\s', remote_cmd):     # 登陆远程主机的命令是否带有-i选项
                        ssh.interact()
                        exit(0)

                    ssh.expect('password:', timeout=self.timeout)
                    ssh.sendline(self.password)
                    ssh.interact()
                    exit(0)

            ssh.interact()
            exit(0)
        except pexpect.EOF:
            print 'ERROR: sub process abort unfortinately'
            ssh.close()
            exit(400)
        except pexpect.TIMEOUT:
            print 'ERROR: pexpect timeout.'
            ssh.close()
            exit(400)

    def pexpect_key(self, cmd, remote_cmd=None):
    # cmd参数表示能够直接登陆的服务器命令（[NormalServer]列表下），remote_cmd参数表示通过jumper服务器才能登陆的命令（[NeedJumpServer]列表下）
        try:
            ssh = pexpect.spawn(cmd, timeout=self.timeout)  # logfile=sys.stdout

            # 跳板机
            if remote_cmd:
                user_type = ssh.expect([']#', ']$'], timeout=self.timeout)
                if user_type in (0, 1):
                    ssh.sendline(remote_cmd)
                    if re.search('\s-i\s', remote_cmd):     # 登陆远程主机的命令是否带有-i选项
                        ssh.interact()
                        exit(0)
                    ssh.expect('password:', timeout=self.timeout)
                    ssh.sendline(self.password)
                    exit(0)

            ssh.interact()
            exit(0)
        except pexpect.EOF:
            print 'ERROR: sub process abort unfortinately'
            exit(400)
        except pexpect.TIMEOUT:
            print 'ERROR: pexpect timeout.'
            exit(400)

    # SSH 连接
    def login(self):
        # 密码登陆远程主机
        if self.private_key == "None":
            cmd = "ssh -o ConnectTimeout=%s -o StrictHostKeyChecking=no -p %s %s@%s" \
                % (self.timeout, self.port, self.username, self.host)
            print 'The command to login on the remote service:\n\t%s' % cmd
            if self.debug_switch == 0:
                self.pexpect_passwd(cmd)
        # 密钥登陆远程主机
        cmd = "ssh -o ConnectTimeout=%s -o StrictHostKeyChecking=no -i %s -p %s %s@%s" \
            % (self.timeout, self.private_key, self.port, self.username, self.host)
        print 'The command to login on the remote service:\n\t%s' % cmd
        if self.debug_switch == 0:
            self.pexpect_key(cmd)


    # SCP 上传本地文件/文件夹到远程服务器
    def upload(self, files, dest_dir):
        files = re.sub(r'\[\'|\'\,\s\'|\'\]', ' ', str(files))
        if self.private_key == "None":
            cmd = "scp -o ConnectTimeout=%s -o StrictHostKeyChecking=no -P %s %s %s@%s:%s" \
                  % (self.timeout, self.port, files, self.username, self.host, dest_dir)
            print cmd
            if self.debug_switch == 0:
                self.pexpect_passwd(cmd)

        cmd = "scp -o ConnectTimeout=%s -o StrictHostKeyChecking=no -i %s -P %s %s %s@%s:%s" \
              % (self.timeout, self.private_key, self.port, files, self.username, self.host, dest_dir)
        print 'The command to login on the remote service:\n\t%s' % cmd
        if self.debug_switch == 0:
            self.pexpect_key(cmd)

    # SCP 从远程服务器下载文件/文件夹到本地
    def dowmload(self, files, dest_dir):
        for file in files:
            if self.private_key == "None":
                cmd = "scp -o ConnectTimeout=%s -o StrictHostKeyChecking=no -P %s %s@%s:%s %s" \
                      % (self.timeout, self.port, self.username, self.host, file, dest_dir)
                print 'The command to login on the remote service:\n\t%s' % cmd
                if self.debug_switch == 0:
                    self.pexpect_passwd(cmd)
                exit(0)

            cmd = "scp -o ConnectTimeout=%s -o StrictHostKeyChecking=no -i %s -P %s %s@%s:%s %s" \
                  % (self.timeout, self.private_key, self.port, self.username, self.host, file, dest_dir)
            print 'The command to login on the remote service:\n\t%s' % cmd
            if self.debug_switch == 0:
                self.pexpect_key(cmd)
            exit(0)

    # 需要跳板机的 SSH 连接
    def jump_login(self, jump_username, jump_host, jump_port, jump_password, jump_private_key):
        # 用密码登陆跳板机
        if self.private_key == "None":
            remote_cmd = "ssh -o ConnectTimeout=%s -o StrictHostKeyChecking=no -p %s %s@%s" \
                  % (self.timeout, self.port, self.username, self.host)
            # 用密码登陆远程主机
            if jump_private_key == "None":
                cmd = "ssh -o ConnectTimeout=%s -o StrictHostKeyChecking=no -p %s %s@%s" \
                      % (self.timeout, jump_port, jump_username, jump_host)
                print 'The command to login on the jumper service:\n\t%s' % cmd
                print 'The command to login on the remote service:\n\t%s' % remote_cmd
                if self.debug_switch == 0:
                    self.pexpect_passwd(cmd, remote_cmd, jump_password)
                exit(0)
            # 用密钥登陆远程主机
            cmd = "ssh -o ConnectTimeout=%s -o StrictHostKeyChecking=no -i %s -p %s %s@%s" \
                % (self.timeout, jump_private_key, jump_port, jump_username, jump_host)
            print 'The command to login on the jumper service:\n\t%s' % cmd
            print 'The command to login on the remote service:\n\t%s' % remote_cmd
            if self.debug_switch == 0:
                self.pexpect_passwd(cmd, remote_cmd)
            exit(0)

        # 用密钥登陆跳板机
        remote_cmd = "ssh -o ConnectTimeout=%s -o StrictHostKeyChecking=no -i %s -p %s %s@%s" \
              % (self.timeout, self.private_key, self.port, self.username, self.host)
        # 用密码登陆远程主机
        if jump_private_key == "None":
            cmd = "ssh -o ConnectTimeout=%s -o StrictHostKeyChecking=no -p %s %s@%s" \
                  % (self.timeout, jump_port, jump_username, jump_host)
            print 'The command to login on the jumper service:\n\t%s' % cmd
            print 'The command to login on the remote service:\n\t%s' % remote_cmd
            if self.debug_switch == 0:
                self.pexpect_passwd(cmd, remote_cmd)
            exit(0)

        cmd = "ssh -o ConnectTimeout=%s -o StrictHostKeyChecking=no -i %s -p %s %s@%s" \
            % (self.timeout, jump_private_key, jump_port, jump_username, jump_host)
        print 'The command to login on the jumper service:\n\t%s' % cmd
        print 'The command to login on the remote service:\n\t%s' % remote_cmd
        if self.debug_switch == 0:
            self.pexpect_passwd(cmd, remote_cmd)
        exit(0)

# 检查环境变量
def check_env():
    init_cfg_data = '''NAME   HOST   PORT  USER  PASS   KEY    JUMP_TAG  DESCRIBE
[Normal Server]
my_host1  192.168.1.20  22  root  123456  None    0  测试机（用密码登陆的）
my_jump  192.168.1.162  22  root  None  key_file    0  跳板机（用密钥登陆）

[Need Jump Server]
my_host2  192.168.2.100  22  root  789123  None    1  需要跳板机才能登陆的测试机（用密码登陆）
'''
    env = Check()
    env.init_cfg_file(RUNSSH_CONFIG, init_cfg_data)
    ck_timeout = env.int_range(RUNSSH_TIMEOUT, start_point=5, end_point=60, hint='RUNSSH_TIMEOUT')
    ck_switch = env.switch(RUNSSH_SWITCH, hint='RUNSSH_SWITCH')
    if ck_timeout != None:
        print ck_timeout
        exit(400)
    if ck_switch != None:
        print ck_switch
        exit(400)

# 检查配置文件
def check_conf():
    sshconf = CredentialOptions(RUNSSH_CONFIG, reg_remove='^NAME.*|^\[.*')
    content = sshconf.read(
        dict_fields=['line', 'name', 'host', 'port', 'username', 'password', 'privateKey', 'jumpTag', 'describe'])
    _content = jsonpath(json.loads(content), expr='$..Content')[0]
    for info in _content:
        line = jsonpath(info, expr='$..line')[0]
        name = jsonpath(info, expr='$..name')[0]
        host = jsonpath(info, expr='$..host')[0]
        port = jsonpath(info, expr='$..port')[0]
        username = jsonpath(info, expr='$..username')[0]
        private_key = jsonpath(info, expr='$..privateKey')[0]
        jump_tag = jsonpath(info, expr='$..jumpTag')[0]

        conf = Check()
        ck_name = conf.name(name, hint='Line: %s  Field: NAME' % line)
        ck_host = conf.host(host, hint='Line: %s  Field: PORT\n\t' % line)
        ck_port = conf.int_range(port, hint='Line: %s  Field: PORT\n\t' % line)
        ck_user = conf.name(username, hint='Line: %s  Field: USER' % line)
        ck_key = conf._isfile(private_key, RUNSSH_DEFAULT_KEY_PATH, hint='Line: %s  Field: KEY\n\t' % line)
        ck_jtag = conf.switch(jump_tag, hint='Line: %s  Field: JumpTag\n\t' % line)


        if ck_name != None:
            print ck_name
            exit(400)
        if ck_host != None:
            print ck_host
            exit(400)
        if ck_port != None:
            print ck_port
            exit(400)
        if ck_user != None:
            print ck_user
            exit(400)
        if ck_jtag != None:
            print ck_jtag
            exit(400)
        if private_key != "None" and ck_key != None:
            print ck_key
            exit(400)





def get_service_parameters(dest_name, jump_name=None):      # dest_name 目标主机；jump_name跳板机，-j选项
    sshconf = CredentialOptions(RUNSSH_CONFIG, reg_remove='^NAME.*|^\[.*')
    content = sshconf.read(
        type_localtion=('jumpTag', 'normalServer', 'needJumpServer'),
        dict_fields=['line', 'name', 'host', 'port', 'username', 'password', 'privateKey', 'jumpTag', 'describe'])

    if jump_name:
        need_jump = jsonpath(json.loads(content), expr='$..normalServer')[0]
        count = 0
        for nj in need_jump:
            name = jsonpath(nj, expr='$..name')[0]
            jump_host = jsonpath(nj, expr='$..host')[0]
            if name == jump_name or jump_host == jump_name:
                jump_username = jsonpath(nj, expr='$..username')[0]
                jump_port = jsonpath(nj, expr='$..port')[0]
                jump_password = jsonpath(nj, expr='$..password')[0]
                jump_private_key = jsonpath(nj, expr='$..privateKey')[0]
                break
            count = count + 1
        if count == len(need_jump):
            output.not_found('The information with the NAME %s could not be found in %s' % (jump_name, RUNSSH_CONFIG))

        normal = jsonpath(json.loads(content), expr='$..needJumpServer')[0]
        count = 0
        for nm in normal:
            name = jsonpath(nm, expr='$..name')[0]
            host = jsonpath(nm, expr='$..host')[0]
            if name == dest_name or host == dest_name:
                username = jsonpath(nm, expr='$..username')[0]
                port = jsonpath(nm, expr='$..port')[0]
                password = jsonpath(nm, expr='$..password')[0]
                private_key = jsonpath(nm, expr='$..privateKey')[0]
                break
            count = count + 1
        if count == len(normal):
            output.not_found('The information with the NAME %s could not be found in %s' % (dest_name, RUNSSH_CONFIG))
        return ([username, host, port, password, private_key, RUNSSH_TIMEOUT, RUNSSH_SWITCH],
                          [jump_username, jump_host, jump_port, jump_password, jump_private_key])
    else:
        normal = jsonpath(json.loads(content), expr='$..normalServer')[0]
        count = 0
        for nm in normal:
            name = jsonpath(nm, expr='$..name')[0]
            host = jsonpath(nm, expr='$..host')[0]
            if name == dest_name or host == dest_name:
                username = jsonpath(nm, expr='$..username')[0]
                port = jsonpath(nm, expr='$..port')[0]
                password = jsonpath(nm, expr='$..password')[0]
                private_key = jsonpath(nm, expr='$..privateKey')[0]
                break
            count = count + 1
        if count == len(normal):
            output.not_found('The information with the NAME %s could not be found in %s' % (dest_name, RUNSSH_CONFIG))
        return (username, host, port, password, private_key, RUNSSH_TIMEOUT, RUNSSH_SWITCH)



def usage():
    global args, cert_parser, normal_parser, check_parser, version_parser
    format_class = argparse.RawTextHelpFormatter
    parser = argparse.ArgumentParser(
        usage=' %(prog)s command',
        formatter_class=format_class,
        add_help=True,
    )
    # description = '首行信息：',
    # epilog = '莫行信息：',
    # metavar
    # https: // cloud.tencent.com / developer / ask / 51594

    # 无参数选项，优先级： --help > --check-env > --check-conf
    parser.add_argument('-v', dest='version', action="store_true",
                        help='查看版本号')
    parser.add_argument('--check-env', dest='env', action="store_true",
                        help='检查%(prog)s环境变量，并将环境变量输出')
    parser.add_argument('--check-conf', dest='conf', action="store_true",
                        help='检查%s配置文件中的字段是否合法' % RUNSSH_CONFIG)

    # 互斥选项
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-j', '--jump', dest='jump_name',
                        help='当目标主机需要跳板机登陆时，指定跳板机NAME')
    group.add_argument('-u', '--upload', dest='local_files', nargs='+',
                       help='将本地文件/文件夹上传到远程主机。默认接收路径：/tmp/ ，通过-D选项可更改路径')
    group.add_argument('-d', '--download', dest='remote_files', nargs='+',
                       help='从远程主机下载文件/文件夹到本地。默认接收路径：/tmp/ ，通过-D选项可更改路径')

    # 其他选项，--search > other
    parser.add_argument('-D', '--destination', dest='dest_dir',
                        default='/tmp/', help='--download 或 --upload的时候，需要此参数指定接收路径')

    parser.add_argument('--search', dest='search_reg',
                        help='模糊匹配%s中的 NAME|HOST 字段，将查询结果输出。默认是normal类型的服务器，通过--type来更改类型' % RUNSSH_CONFIG)
    parser.add_argument('--type', dest='type', choices=['normal', 'needjump'],
                        default='normal', help='--search的时候，可以用此参数更改要查询的服务器类型。默认值：normal')


    reg = '^-+[a-zA-Z]+'
    no_param_opt = ['-h', '--help', '-v', '--check-env', '--check-conf']
    no_host_param_opt = ['--search', '--type']
    param_opt = ['-j', '--jump', '-u', '--upload', '-d', '--download', '-D', '--destination', '--field']


    # 无参数选项
    if re.match(reg, sys.argv[-1]) and sys.argv[-1] in no_param_opt:
        options = sys.argv[1:]
    # 无需 IP/HOST/NAME 的选项
    elif re.match(reg, sys.argv[-2]) and sys.argv[-2] in no_host_param_opt:
        options = sys.argv[1:]
    # 无效选项
    elif re.match(reg, sys.argv[-1].strip()) and sys.argv[-1] not in param_opt:
        output.invalid_option(sys.argv[-1])
    else:
        options = sys.argv[1:-1]

    args = parser.parse_args(options)



if __name__ == '__main__':
    global RUNSSH_CONFIG, RUNSSH_TIMEOUT, RUNSSH_SWITCH
    global version, output
    # 环境变量
    ## RUNSSH配置文件绝对路径
    RUNSSH_CONFIG = os.environ.get("RUNSSH_CONFIG") if "RUNSSH_CONFIG" in os.environ else '/tmp/runssh.conf'
    ## RUNSSH连接超时时间
    RUNSSH_TIMEOUT = os.environ.get("RUNSSH_TIMEOUT") if "RUNSSH_TIMEOUT" in os.environ else 10
    ## 调试开关 1：开 0：关
    RUNSSH_SWITCH = os.environ.get("RUNSSH_SWITCH") if "RUNSSH_SWITCH" in os.environ else 0
    ## 默认密钥存放路径
    RUNSSH_DEFAULT_KEY_PATH = os.environ.get("RUNSSH_DEFAULT_KEY_PATH") if "RUNSSH_DEFAULT_KEY_PATH" in os.environ else '~/.ssh'

    # 参数
    version = '1.0.0'

    reload(sys)
    sys.setdefaultencoding('utf8')
    output = Output()
    usage()
    try:
        if sys.argv[-1] == sys.argv[0]:
            output.format_error()
        if args.version:
            print "Version: %s" % version
            exit(0)
        if args.env:
            check_env()
            print 'INFO: Environment variable checked. [OK]'
            exit(0)
        if args.conf:
            check_conf()
            print "INFO: Configure file checked. [OK]"
            exit(0)

        check_env()
        check_conf()

        _name = sys.argv[-1]
        if args.search_reg:
            search = CredentialOptions(RUNSSH_CONFIG)
            print search.search(args.search_reg, args.type)
            exit(0)
        if args.jump_name:
            param, jump_param = get_service_parameters(_name, args.jump_name)
            _jump = Command(*param)
            _jump.jump_login(*jump_param)
            exit(0)
        param = get_service_parameters(_name)
        if args.local_files:
            _upload = Command(*param)
            _upload.upload(args.local_files, args.dest_dir)
            exit(0)
        if args.remote_files:
            _dowmload = Command(*param)
            _dowmload.dowmload(args.remote_files, args.dest_dir)
            exit(0)

        _login = Command(*param)
        _login.login()

    except IndexError:
        output.format_error()
    except (Exception, AttributeError) as e:
        print "ERROR: An unknown error.%s" % e
    except KeyboardInterrupt:
        print "Exit."
        exit(400)









