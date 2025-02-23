# NetEaseService
网易云服务端
# 启动登录注册服务
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
# 启动Websocke服务
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
