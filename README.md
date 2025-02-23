# NetEaseService
网易云信服务端含登录、注册、数据库、websocke连接
# 启动登录注册服务
可用于用户注册登录，数据保存至数据库、数据库已配置
```
python3 service.py
```
注册api接口
```
http://localhost:5001/create_account
```
登录api接口
```
http://localhost:5001/login
```
查询所有用户数据
```
http://localhost:5001/users
```
# 启动Websocke服务
websocke服务用于查询用户连接服务器数据，并且能够实现获取当前用户操作
```
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
或者
```
python3 main.py
```
查询连接用户数据：
```
curl http://localhost:8000/connected_clients
```
返回示例
```
{
  "connected_clients": [
    "android123"
  ]
}
```
查询指定用户当前数据
```
# 用户Id例：android123
curl http://localhost:8000/get_input/android123
```
返回示例
```
{
  "android_id": "android123",
  "input_content": "Hello World!"
}
```
