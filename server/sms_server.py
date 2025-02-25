import random
import redis
from flask import Flask, request, jsonify
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

# 初始化 Flask 应用
app = Flask(__name__)

# Redis 配置
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

# 阿里云配置
ACCESS_KEY_ID = 'LTAI5tRjty3uvxKAP9HRFapu'
ACCESS_KEY_SECRET = '3jSzla6GmUxnD2QfcC3R8NF2UlodOt'
SIGN_NAME = '谈信'
TEMPLATE_CODE = 'SMS_479055455'

# 生成验证码
def generate_verification_code():
    return str(random.randint(100000, 999999))

# 发送短信验证码
def send_sms_code(phone_number):
    code = generate_verification_code()

    # 将验证码存储到 Redis，设置过期时间（5分钟）
    redis_client.setex(phone_number, 300, code)

    # 阿里云短信发送配置
    client = AcsClient(ACCESS_KEY_ID, ACCESS_KEY_SECRET, 'cn-hangzhou')
    request = CommonRequest()
    request.set_method('POST')
    request.set_domain('dysmsapi.aliyuncs.com')
    request.set_version('2017-05-25')
    request.set_action_name('SendSms')

    request.add_query_param('PhoneNumbers', phone_number)
    request.add_query_param('SignName', SIGN_NAME)
    request.add_query_param('TemplateCode', TEMPLATE_CODE)
    request.add_query_param('TemplateParam', '{"code":"' + code + '"}')

    response = client.do_action_with_exception(request)
    return response

# 发送验证码的接口
@app.route('/send_sms_code', methods=['POST'])
def api_send_sms_code():
    data = request.json
    phone_number = data.get('phone_number')

    # 调用发送短信的函数
    try:
        response = send_sms_code(phone_number)
        return jsonify({"success": True, "message": "验证码已发送", "response": response.decode('utf-8')})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# 验证短信验证码的接口
@app.route('/verify_sms_code', methods=['POST'])
def api_verify_sms_code():
    data = request.json
    phone_number = data.get('phone_number')
    input_code = data.get('code')

    # 从 Redis 获取存储的验证码
    stored_code = redis_client.get(phone_number)

    if not stored_code:
        return jsonify({"success": False, "message": "验证码已过期或未发送"})

    # 比较输入的验证码与存储的验证码
    if input_code == stored_code:
        return jsonify({"success": True, "message": "验证码验证成功"})
    else:
        return jsonify({"success": False, "message": "验证码错误"})

# 启动应用
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
