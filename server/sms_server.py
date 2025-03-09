import random
import time
from alibabacloud_dysmsapi20170525.client import Client as DysmsapiClient
from alibabacloud_tea_openapi import models as open_api_models
from flask import Flask, request, jsonify

app = Flask(__name__)

# 配置信息 - 替换为你的实际信息
ACCESS_KEY_ID = '94e2d4e8e64665e47d04e4f4e6d1840a'
ACCESS_KEY_SECRET = '47d1496b029a'
SIGN_NAME = '谈信'
TEMPLATE_CODE = 'SMS_313101151'  # 模板CODE

# 内存存储验证码（生产环境建议用Redis）
verification_codes = {}

def create_client() -> DysmsapiClient:
    config = open_api_models.Config(
        access_key_id=ACCESS_KEY_ID,
        access_key_secret=ACCESS_KEY_SECRET
    )
    config.endpoint = 'dysmsapi.aliyuncs.com'
    return DysmsapiClient(config)

def generate_code(length=6):
    """生成指定位数随机数字验证码"""
    return ''.join(random.choices('0123456789', k=length))

@app.route('/send_code', methods=['POST'])
def send_verification_code():
    mobile = request.json.get('mobile')
    if not mobile:
        return jsonify({'code': 400, 'message': '手机号不能为空'})
    
    # 生成验证码
    code = generate_code()
    verification_codes[mobile] = {
        'code': code,
        'timestamp': time.time()
    }
    
    try:
        client = create_client()
        send_request = {
            'phone_numbers': mobile,
            'sign_name': SIGN_NAME,
            'template_code': TEMPLATE_CODE,
            'template_param': f'{{"code":"{code}"}}'
        }
        response = client.send_sms(send_request)
        if response.body.code == 'OK':
            return jsonify({'code': 200, 'message': '验证码已发送'})
        else:
            return jsonify({'code': 500, 'message': f'发送失败: {response.body.message}'})
    except Exception as e:
        return jsonify({'code': 500, 'message': f'服务器错误: {str(e)}'})

@app.route('/verify_code', methods=['POST'])
def verify_code():
    mobile = request.json.get('mobile')
    user_code = request.json.get('code')
    
    stored_data = verification_codes.get(mobile)
    if not stored_data:
        return jsonify({'code': 400, 'message': '请先获取验证码'})
    
    # 检查有效期（5分钟）
    if time.time() - stored_data['timestamp'] > 300:
        del verification_codes[mobile]
        return jsonify({'code': 400, 'message': '验证码已过期'})
    
    if user_code == stored_data['code']:
        del verification_codes[mobile]
        return jsonify({'code': 200, 'message': '验证成功'})
    else:
        return jsonify({'code': 400, 'message': '验证码错误'})

if __name__ == '__main__':
    app.run(debug=True)
