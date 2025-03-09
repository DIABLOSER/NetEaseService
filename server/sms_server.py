import os
import random
import time
from alibabacloud_dysmsapi20170525.client import Client as DysmsapiClient
from alibabacloud_tea_openapi import models as open_api_models
from flask import Flask, request, jsonify
from flask_cors import CORS  # 解决跨域问题

app = Flask(__name__)
CORS(app)  # 允许所有跨域请求
app.config['JSON_AS_ASCII'] = False  # 支持中文显示

# 配置信息（从环境变量获取，测试时可直接赋值）
ACCESS_KEY_ID = '94e2d4e8e64665e47d04e4f4e6d1840a'
ACCESS_KEY_SECRET = '47d1496b029a'
SIGN_NAME = '谈信'
TEMPLATE_CODE = 'SMS_313101151'  # 模板CODE

# 内存存储验证码（生产环境替换为Redis）
verification_codes = {}

def create_client():
    """创建阿里云客户端"""
    config = open_api_models.Config(
        access_key_id=ACCESS_KEY_ID,
        access_key_secret=ACCESS_KEY_SECRET
    )
    config.endpoint = 'dysmsapi.aliyuncs.com'
    return DysmsapiClient(config)

@app.errorhandler(Exception)
def handle_exception(e):
    """全局异常处理"""
    return jsonify({
        "code": 500,
        "message": f"服务器错误: {str(e)}"
    }), 500

@app.route('/send_code', methods=['POST'])
def send_verification_code():
    """发送验证码接口"""
    # 请求数据校验
    if not request.is_json:
        return jsonify({"code": 400, "message": "请求必须为JSON格式"}), 400
    
    data = request.get_json()
    mobile = data.get('mobile')
    
    # 参数验证
    if not mobile:
        return jsonify({"code": 400, "message": "手机号不能为空"}), 400
    
    if not mobile.startswith('+'):
        return jsonify({"code": 400, "message": "手机号需国际格式（如：+8613812345678）"}), 400

    # 生成6位验证码
    code = ''.join(random.choices('0123456789', k=6))
    verification_codes[mobile] = {
        'code': code,
        'timestamp': time.time()
    }
    
    # 打印验证码到控制台（测试时使用）
    print(f"[DEBUG] 手机号 {mobile} 的验证码：{code}（有效期5分钟）")
    
    # 正式发送短信（测试时可注释）
    try:
        client = create_client()
        response = client.send_sms({
            'phone_numbers': mobile,
            'sign_name': SIGN_NAME,
            'template_code': TEMPLATE_CODE,
            'template_param': f'{{"code":"{code}"}}'
        })
        if response.body.code == 'OK':
            return jsonify({"code": 200, "message": "验证码已发送"})
        else:
            return jsonify({
                "code": 500,
                "message": f"短信发送失败：{response.body.message}"
            }), 500
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"短信服务异常：{str(e)}"
        }), 500

@app.route('/verify_code', methods=['POST'])
def verify_code():
    """验证码校验接口"""
    if not request.is_json:
        return jsonify({"code": 400, "message": "请求必须为JSON格式"}), 400
    
    data = request.get_json()
    mobile = data.get('mobile')
    user_code = data.get('code')
    
    # 参数验证
    if not all([mobile, user_code]):
        return jsonify({"code": 400, "message": "参数不完整"}), 400
    
    # 验证码校验
    record = verification_codes.get(mobile)
    if not record:
        return jsonify({"code": 400, "message": "请先获取验证码"}), 400
    
    # 有效期检查（5分钟）
    if time.time() - record['timestamp'] > 300:
        del verification_codes[mobile]
        return jsonify({"code": 400, "message": "验证码已过期"}), 400
    
    # 验证码比对
    if user_code == record['code']:
        del verification_codes[mobile]
        return jsonify({"code": 200, "message": "验证成功"})
    else:
        return jsonify({"code": 400, "message": "验证码错误"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
