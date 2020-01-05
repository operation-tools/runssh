# RUNSSH
## 简介：
本脚本基于ssh/scp命令用于解决Mac OS、Linux OS无法保存SSH凭证信息的问题。<br>
该脚本仅用于python 2，如果需要在python 3下使用，请坐对应的修改。
## 安装runssh：
安装runssh
```
$ git clone https://github.com/operation-tools/runssh.git
$ sudo cp runssh/code/runssh.py /usr/local/bin/runssh
$ sudo chmod 755 /usr/local/bin/runssh
$ sudo pip2.7 install pexpect jsonpath OrderedDict argparse
$ runssh -h      # display HELP manual
```

如果没有pip命令，可以使用下方命令安装（存在pip命令请跳过此步骤）
```
$ curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
$ sudo python get-pip.py
```

## 使用之前：
### runssh的环境变量介绍：

  环境变量  | 作用 | 默认值 | 格式
  ------------- | -------------  | ------------- | ------------- 
 RUNSSH_CONFIG  | 配置文件（指定存放ssh凭证信息的文件） | ~/.runssh/runssh.conf | 必须为绝对路径
 RUNSSH_TIMEOUT | ssh与pexpect命令超时时间  | 10 | int()<br>建议在5~10秒
 RUNSSH_SWITCH  | 调试开关（是否执行pexpect命令） | 0 表示关闭调试开关，执行pexpect命令 | 0 或 1
 RUNSSH_DEFAULT_KEY_PATH | 配置文件中[NormalServer]组里面KEY字段的相对路径 | ~/.ssh/ | KEY字段使用相对路径表示时，如：id_rsa，结果（补全）：~/.ssh/id_rsa<br>KEY字段使用绝对路径表示时，如：/tmp/id_rsa，结果：/tmp/id_rsa
 
 
### 更改环境变量：

- 设置环境变量：
```
$ vim ~/.bash_profile   # 添加环境变量
    ... ... // 原文内容省略
    export RUNSSH_CONFIG='/home/user/.runssh/runssh.conf'

$ source ~/.bash_profile
$ runssh --check-env
    INFO: Environment variable checked. [OK]
$ cat ~/.runssh/runssh.conf     # 检查环境变量成功会生成一个默认的配置文件
    NAME   HOST   PORT  USER  PASS   KEY    JUMP_TAG  DESCRIBE
    [Normal Server]
    my_host1  192.168.1.20  22  root  123456  None    0  测试机（用密码登陆的）
    my_jump  192.168.1.162  22  root  None  key_file    0  跳板机（用密钥登陆）
    
    [Need Jump Server]
    my_host2  192.168.2.100  22  root  789123  None    1  需要跳板机才能登陆的测试机（用密码登陆）  
```
- 如果你对你的配置不放心，可以开启调试模式：
```
$ vim ~/.bash_profile   # 添加环境变量
    ... ... // 原文内容省略
    export RUNSSH_SWITCH='1'
    

这样的话，你执行任何命令都不会执行SSH/SCP命令，只会在终端输出对应的命令。
```
    
### 配置文件解析：

  字段  | 作用 | 格式
  ------------- | -------------  | -------------
 NAME  | 用于ssh连接的别名 | 字母开头，字母或数字结尾，中间可包含字母数字-_，不包含其他特殊字符
 HOST | 远程主机的 IP 或 域名  | 满足IP/域名格式
 PORT  | 远程主机的端口 | 1~65535
 PASS | 远程主机的密码 | 暂无限制（不使用时，设置为None）
 KEY | 远程主机的密钥 | 支持相对路径和绝对路径（优先级高于PASS，不使用时设置为None）。相对路径基于RUNSSH_DEFAULT_KEY_PATH变量
 JUMP_TAG | 是否需要跳板机才能登陆 | 1 需要； 0 不需要
 DESCRIBE | 描述信息 | 暂无限制
 
- 其他注意事项：
    * 第一行、[Normal Server]、[Need Jump Server] 这三行请勿删除；
    * 使用之前请把默认的主机配置KEY字段设置为None或者删除；
    * [Normal Server] JumpTag字段为0的组，此组填写不需要跳板机登陆的服务器（不按此要求写不会影响脚本使用，仅仅为了方便管理）；
    * [Need Jump Server] JumpTag字段为1的组，此组填写需要跳板机登陆的服务器（不按此要求写不会影响脚本使用，仅仅为了方便管理）；
 


## 开始使用：
### 开始一切操作之前请确保你已经添加了主机配置：
```
$ cat ~/.runssh/runssh.conf
    NAME   HOST   PORT  USER  PASS   KEY    JUMP_TAG  DESCRIBE
    [Normal Server]
    my_host1  192.168.1.73  22  wuhl  960510  None    0  测试机（用密码登陆的）
    my_jump  192.168.1.20  22  root  None  id_rsa    0  跳板机（用密钥登陆）
    
    [Need Jump Server]
    my_host2  192.168.2.100  22  root  789123  None    1  需要跳板机才能登陆的测试机（用密码登陆）


$ runssh --check-conf
    INFO: Configure file checked. [OK]
```

### SSH连接：
- 密码登陆：
```
$ runssh my_host1   或  $ runssh 192.168.1.73

等于下方命令
ssh -o ConnectTimeout=10  -o StrictHostKeyChecking=no  -p 22 root@192.168.1.73
```

- 密钥登陆：
```
$ runssh my_jump   或  $ runssh 192.168.1.20

等于下方命令:
ssh -o ConnectTimeout=10  -o StrictHostKeyChecking=no  -i ～/.ssh/id_rsa -p 22 root@192.168.1.20
```

- 使用跳板机登陆：
```
场景：
    Client -> Host1  // can ssh successful
    Host1 -> Host2   // can ssh 
successful    Client -X Host2  // can't ssh 
successful

原理：
     Client -> Host1 -> Host2   // can ssh successful
     
     
$ runssh -j my_jump my_host2

等于下方命令：
ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i ~/id_rsa -p 22 root@192.168.1.20    # 登陆到跳板机
ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -p 22 root@192.168.2.100   # 在跳板机上在执行一次ssh命令

注意事项：
    [Need Jump Server]组里面的主机KEY如果使用相对路径，表示您的KEY文件是~/.ssh/key_name；
    此组里面的相对路径不受环境变量RUNSSH_DEFAULT_KEY_PATH影响。
```

### SCP 从远程主机下载或上传文件/文件夹：
- scp 上传文件：
```
$ runssh -u /tmp/file.txt -D /root/ my_jump

等于下方命令：
scp -r -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i /home/wuhaolai/.ssh/id_rsa -P 22  /tmp/file.txt  root@192.168.1.20:/root/
```

- scp 上传文件夹和文件：
```
$ runssh -u /tmp/file.txt /tmp/dir/ my_host1

不指定-D，默认路径为：/tmp/
等于下方命令：
scp -r -o ConnectTimeout=10 -o StrictHostKeyChecking=no -P 22  /tmp/file.txt /tmp/dir/  wuhl@192.168.1.73:/tmp/
```

- scp 下载：
```
$ runssh -d /root/file.txt -D ./  my_jump

等于下方命令：
scp -r -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i /home/wuhaolai/.ssh/id_rsa -P 22 root@192.168.1.20:/root/file.txt ./


下载命令有缺陷，因为远程主机的路径不能用tab键补全。
```

### search正则匹配（python re正则表达式）：
```
比如我们忘记了我们定义的NAME或HOST，但是我们只记得一个大概：

$ runssh --search '.*jum\w' | jq        # 返回json字符串，jq命令可以整理json数据
    {
      "normal": [
        {
          "username": "root",
          "describe": "跳板机（用密钥登陆）",
          "name": "my_jump",
          "jumpTag": "0",
          "privateKey": "id_rsa",
          "host": "192.168.1.20",
          "line": "4",
          "password": "None",
          "port": "22"
        }
      ]
    }

默认是查看[NormalServer]组里面的，如果我们想看[NeedJumpServer]组里面的主机，使用--type选项：
$ runssh --search '.*host' --type needjump | jq
    {
      "needjump": [
        {
          "username": "wuhl",
          "describe": "测试机（用密码登陆的）",
          "name": "my_host1",
          "jumpTag": "0",
          "privateKey": "None",
          "host": "192.168.1.73",
          "line": "3",
          "password": "960510",
          "port": "22"
        }
      ]
    }
```





