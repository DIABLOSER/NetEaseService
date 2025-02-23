# NetEaseService
网易云信（Netease Cloud Communication）是由网易公司推出的一项即时通讯服务平台，提供高性能、高可靠的即时消息和实时音视频通信能力。它支持多种应用场景，包括社交、在线教育、企业协作、在线客服、直播互动等。网易云信的核心优势在于其灵活的 API、SDK 及全套通信能力，帮助开发者快速集成各种实时通信功能。

网易云信服务端含登录、注册、数据库、websocke连接

参考[网易云信服务端API]([URL](https://doc.yunxin.163.com/messaging2/server-apis/jA1MTQ4MDU?platform=server))

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
