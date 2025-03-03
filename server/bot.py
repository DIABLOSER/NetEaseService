import os
import json
import time
import hashlib
import requests
from flask import Flask, request, jsonify

# ========== 配置区域 ==========
APP_KEY = "94e2d4e8e64665e47d04e4f4e6d1840a"        # 替换为你的AppKey
APP_SECRET = "47d1496b029a"  # 替换为你的AppSecret
CALLBACK_URL = "http://47.122.128.122:5004/callback"  # 需公网可访问
# =============================
BOT_ACCOUNT = "123"  # 机器人账号
# =============================

# 生成鉴权校验码
def generate_checksum(app_secret, nonce, curtime):
    content = f"{app_secret}{nonce}{curtime}".encode('utf-8')
    return hashlib.sha1(content).hexdigest()

# 发送文本消息（同步）
def send_text_message(from_accid, to_accid, text):
    url = "https://api.netease.im/nimserver/msg/sendMsg.action"
    
    nonce = os.urandom(16).hex()
    curtime = str(int(time.time()))
    checksum = generate_checksum(APP_SECRET, nonce, curtime)
    
    headers = {
        "AppKey": APP_KEY,
        "Nonce": nonce,
        "CurTime": curtime,
        "CheckSum": checksum,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    payload = {
        "from": from_accid,
        "ope": 0,  # 0:单聊 1:群聊
        "to": to_accid,
        "type": "0",
        "body": json.dumps({"msg": text})
    }
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        result = response.json()
        if response.status_code == 200 and result.get("code") == 200:
            print(f"消息发送成功 -> {to_accid}")
            return True
        else:
            print(f"发送失败: {result.get('desc')}")
            return False
    except Exception as e:
        print(f"请求异常: {str(e)}")
        return False

# Flask回调服务器
app = Flask(__name__)

@app.route('/callback', methods=['POST'])
def message_callback():
    """
    处理消息回调
    官方文档：https://dev.yunxin.163.com/docs/接口文档/服务端回调事件
    """
    try:
        data = request.json
        
        # 验证回调合法性（可选）
        # 实际生产环境需校验checksum和IP白名单
        
        event_type = data.get("eventType")
        
        # 处理新消息回调
        if event_type == "1":  
            msg_from = data.get("fromAccount")
            msg_body = json.loads(data.get("body", "{}"))
            
            print(f"收到来自 {msg_from} 的消息: {msg_body.get('msg')}")
            
            # 自动回复逻辑
            send_text_message(
                from_accid=BOT_ACCOUNT,  # 机器人账号
                to_accid=msg_from,
                text="[自动回复] 已收到您的消息"
            )
            
        return jsonify({"code": 200})
    
    except Exception as e:
        print(f"回调处理异常: {str(e)}")
        return jsonify({"code": 500, "error": str(e)})

if __name__ == "__main__":
    # 测试发送消息
    send_text_message(
        from_accid=BOT_ACCOUNT,
        to_accid="15756475746",
        text="这是第一条测试消息"
    )
    
    # 启动回调服务器（默认端口5000）
    app.run(host='0.0.0.0', port=5004, debug=False)