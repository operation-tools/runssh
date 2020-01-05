# .read() 读取凭证文件，返回列表或json数据：
## 例子文本内容如下：
        
```
NAME   HOST   PORT  USER  PASS   KEY    JUMP  DESC
[Normal Server]
my_host1  192.168.1.20  22  root  123456  None    0  测试机（用密码登陆的）
my_jump  192.168.1.162  22  root  None  key_file    0  跳板机（用密钥登陆）

[Need Jump Server]
my_host2  192.168.2.100  22  root  789123  None    1  需要跳板机才能登陆的测试机（用密码登陆）
```
## reg_remove参数：
```
不加此参数表示不启用；
如果我不想要 NAME... 、 [Normal Server] 、 [Need Jump Server] 这三行，可这样配置reg_remove='^NAME.*|^\[.*'
```

## type_localtion参数 和 dict_fields=[]参数：
```
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
```