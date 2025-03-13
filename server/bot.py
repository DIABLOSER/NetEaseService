import os
import json
import time
import hashlib
import requests
from flask import Flask, request, jsonify
from datetime import datetime
from config import Config  # 导入配置文件

# ========== 配置区域 ==========
APP_KEY = "94e2d4e8e64665e47d04e4f4e6d1840a"  # 替换为你的AppKey
APP_SECRET = "47d1496b029a"  # 替换为你的AppSecret
CALLBACK_URL = "http://47.122.128.122:5004/callback"  # 需公网可访问
BOT_ACCOUNT = "123"  # 机器人账号
# =============================

# 生成鉴权校验码
def generate_checksum(app_secret, nonce, curtime):
    content = f"{app_secret}{nonce}{curtime}".encode('utf-8')
    return hashlib.sha1(content).hexdigest()

# 发送文本消息（同步）
def send_text_message(from_accid, to_accid, text, is_group=False):
    """
    发送文本消息，支持单聊和群聊
    :param from_accid: 发送者账号
    :param to_accid: 接收者账号（单聊时是用户ID，群聊时是群ID）
    :param text: 消息内容
    :param is_group: 是否为群聊
    :return: 发送结果 True/False
    """
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
        "ope": 1 if is_group else 0,  # 0:单聊, 1:群聊
        "to": to_accid,
        "type": "0",  # 文本消息
        "body": json.dumps({"msg": text})
    }
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        result = response.json()
        if response.status_code == 200 and result.get("code") == 200:
            print(f"[{get_time()}] 消息发送成功 -> {to_accid}")
            return True
        else:
            print(f"[{get_time()}] 发送失败: {result.get('desc')}")
            return False
    except Exception as e:
        print(f"[{get_time()}] 请求异常: {str(e)}")
        return False

# 获取当前时间
def get_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Flask回调服务器
app = Flask(__name__)

@app.route('/callback', methods=['POST'])
def message_callback():
    """
    处理消息回调（支持个人消息和群聊消息）
    """
    try:
        data = request.json
        print(f"[{get_time()}] [DEBUG] 原始回调数据:", data)

        event_type = data.get("eventType")
        msg_from = data.get("fromAccount", "未知用户")
        msg_body = data.get("body", "")

        if event_type == 1:  # 私聊消息
            print(f"[{get_time()}] 收到来自 {msg_from} 的私聊消息: {msg_body}")

            # 自动回复
            send_text_message(
                from_accid=BOT_ACCOUNT,
                to_accid=msg_from,
                text=f"[自动回复] 你说的是: {msg_body}",
                is_group=False
            )

        elif event_type == 2:  # 群聊消息
            group_id = data.get("to")  # 群聊ID
            print(f"[{get_time()}] 收到来自 {msg_from} 在群 {group_id} 的消息: {msg_body}")

            # 避免机器人自己回复自己的消息
            if msg_from != BOT_ACCOUNT:
                send_text_message(
                    from_accid=BOT_ACCOUNT,
                    to_accid=group_id,  # 群聊消息，发送到群ID
                    text=f"[自动回复] {msg_from} 说: {msg_body}",
                    is_group=True
                )

        return jsonify({"code": 200})

    except Exception as e:
        print(f"[{get_time()}] 回调处理异常: {str(e)}")
        return jsonify({"code": 500, "error": str(e)})

if __name__ == "__main__":
    # 测试发送消息
    print(f"[{get_time()}] 发送测试消息...")
    send_text_message(
        from_accid=BOT_ACCOUNT,
        to_accid="15756475746",
        text="这是第一条测试消息",
        is_group=False
    )
    
    # 启动回调服务器
    print(f"[{get_time()}] 服务器启动，监听端口: 5004")
    app.run(host='0.0.0.0', port=5004, debug=True)

