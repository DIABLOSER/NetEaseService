import os
import time
import hashlib
import requests
from flask import Flask, request, jsonify

# ========== 配置区 ==========
APP_KEY = "94e2d4e8e64665e47d04e4f4e6d1840a"          # 从网易云信控制台获取
APP_SECRET = "47d1496b029a"    # 从网易云信控制台获取
SMS_TEMPLATE_ID = "YOUR_TEMPLATE_ID"  # 短信模板ID（需通过审核）
# ============================

# 生成API鉴权校验码
def generate_checksum(app_secret, nonce, curtime):
    content = f"{app_secret}{nonce}{curtime}".encode('utf-8')
    return hashlib.sha1(content).hexdigest()

# ---------------------------
# 发送短信验证码
# ---------------------------
def send_sms(phone_number):
    """
    参数说明：
    - phone_number: 接收短信的手机号（必须带国际区号，如中国+86）
    文档：https://dev.yunxin.163.com/docs/短信服务/服务端API文档
    """
    url = "https://api.netease.im/nimserver/sms/sendcode.action"
    
    # 生成随机6位验证码（生产环境建议使用更安全的方法）
    auth_code = ''.join(str(i % 10) for i in os.urandom(6))
    
    # 生成鉴权参数
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
        "mobile": phone_number,
        "templateid": SMS_TEMPLATE_ID,
        "codeLen": "6",            # 验证码长度
        "authCode": auth_code      # 可选：自定义验证码
    }
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        result = response.json()
        print(f"[短信发送日志] 手机号: {phone_number}, 响应: {result}")
        
        if result.get("code") == 200:
            # 实际生产应将验证码存入数据库/缓存
            return {
                "success": True,
                "request_id": result.get("obj"),  # 网易返回的请求ID
                "auth_code": auth_code            # 实际生产环境不需要返回
            }
        else:
            return {
                "success": False,
                "error_code": result.get("code"),
                "message": result.get("desc")
            }
    except Exception as e:
        return {"success": False, "message": f"API请求异常: {str(e)}"}

# ---------------------------
# 验证短信验证码
# ---------------------------
def verify_sms(phone_number, user_input_code):
    """
    参数说明：
    - phone_number: 待验证手机号
    - user_input_code: 用户输入的验证码
    """
    url = "https://api.netease.im/nimserver/sms/verifycode.action"
    
    # 生成鉴权参数
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
        "mobile": phone_number,
        "code": user_input_code
    }
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        result = response.json()
        print(f"[验证日志] 手机号: {phone_number}, 响应: {result}")
        
        return {
            "valid": result.get("code") == 200,
            "message": result.get("desc", "验证服务异常")
        }
    except Exception as e:
        return {"valid": False, "message": f"API请求异常: {str(e)}"}

# ======================
# HTTP接口示例（Flask）
# ======================
app = Flask(__name__)

@app.route('/sendsms', methods=['POST'])
def handle_send_sms():
    data = request.json
    phone = data.get('phone')
    
    if not phone or len(phone) < 11:
        return jsonify({"success": False, "message": "手机号无效"})
    
    result = send_sms(phone)
    return jsonify(result)

@app.route('/verifysms', methods=['POST'])
def handle_verify_sms():
    data = request.json
    phone = data.get('phone')
    code = data.get('code')
    
    if not all([phone, code]):
        return jsonify({"valid": False, "message": "参数缺失"})
    
    result = verify_sms(phone, code)
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
