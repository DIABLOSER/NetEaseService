from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import requests
import hashlib
import time
import uuid
import jwt
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# 配置多个数据库连接
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///accounts.db'
app.config['SQLALCHEMY_BINDS'] = {
    'images': 'sqlite:///images.db'  # 绑定 images 数据库
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# 创建上传目录
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 网易云信API配置
APP_KEY = '94e2d4e8e64665e47d04e4f4e6d1840a'
APP_SECRET = '47d1496b029a'
SMS_TEMPLATE_ID = "YOUR_TEMPLATE_ID"  # 短信模板ID（需通过审核）
BASE_URL = "https://api.netease.im/nimserver/user/create.action"
SEND_SMS_URL = "https://api.netease.im/sms/sendcode.action"
GROPUP_URL = 'https://api.netease.im/nimserver/team/queryDetail.action'

# 初始化单个 SQLAlchemy 实例
db = SQLAlchemy(app)

# 更新后的用户模型
class User(db.Model):
    __tablename__ = 'users'
    __bind_key__ = None  # 默认数据库连接
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.String(80), unique=True, nullable=False)
    account = db.Column(db.String(80), unique=True, nullable=False)
    token = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    configuration = db.Column(db.Text, default=lambda: json.dumps({
        "enabled": True,
        "p2p_chat_banned": False,
        "team_chat_banned": False,
        "chatroom_chat_banned": False,
        "qchat_chat_banned": False
    }))
    user_information = db.Column(db.Text, default=lambda: json.dumps({
        "name": "",
        "avatar": "",
        "sign": "",
        "email": "",
        "birthday": "",
        "mobile": "",
        "gender": "1",
        "extension": "",
        "antispam_business_id": ""
    }))

# 表情模型
class Image(db.Model):
    __tablename__ = 'images'
    __bind_key__ = 'images'  # 指定使用 images 数据库连接
    id = db.Column(db.String(36), primary_key=True)
    token = db.Column(db.String(32), nullable=False)  # 移除 unique=True
    filename = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255), nullable=False)

    def __init__(self, object_id, token, filename, url):
        self.id = object_id
        self.token = token
        self.filename = filename
        self.url = url

# 先定义会被路由调用的函数
def generate_checksum(secret, nonce, cur_time):
    return hashlib.sha1(f"{secret}{nonce}{cur_time}".encode()).hexdigest()

#=======================================
#创建账号API
#=======================================
def create_im_account(account_id, token, user_info):
    """创建网易云信账号的辅助函数"""
    nonce = str(uuid.uuid4())
    cur_time = str(int(time.time()))
    checksum = generate_checksum(APP_SECRET, nonce, cur_time)

    headers = {
        'AppKey': APP_KEY,
        'Nonce': nonce,
        'CurTime': cur_time,
        'CheckSum': checksum,
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    data = {
        "accid": account_id,
        "token": token,
        "mobile": "15756475746",
        "name": user_info.get('name', account_id),
        "gender": str(user_info.get('gender', 1)),
        "email": user_info.get('email', f"{account_id}@example.com"),
        "birth": user_info.get('birthday', ''),
        "ex": user_info.get('extension', ''),
        "sign": user_info.get('sign', '')
    }

    response = requests.post(BASE_URL, headers=headers, data=data)
    return response.json()
# 创建账号API
@app.route('/create_account', methods=['POST'])
def handle_create_account():
    required_fields = ['account_id', 'account', 'token']
    if not all(request.json.get(field) for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    account_id = request.json['account_id']
    account = request.json['account']
    token = request.json['token']
    
    # 冲突检查
    if User.query.filter((User.account_id == account_id) | 
                      (User.account == account)).first():
        return jsonify({"error": "Account already exists"}), 400

    # 生成默认信息
    default_info = {
        "name": account_id,
        "email": f"{account_id}@example.com",
        "mobile": account
    }

    # 调用已定义的函数
    result = create_im_account(
        account_id=account_id,
        token=token,
        user_info=default_info
    )

    if result.get('code') in [200, 201]:
        try:
            # 创建用户时仅传递必要字段，让模型处理默认值
            new_user = User(
                account_id=account_id,
                account=account,
                token=token
            )
            
            # 如果请求中有额外字段才进行更新
            if 'configuration' in request.json:
                new_user.configuration = json.dumps(request.json['configuration'])
            if 'user_information' in request.json:
                new_user.user_information = json.dumps(request.json['user_information'])

            db.session.add(new_user)
            db.session.commit()
            
            return jsonify({"message": "Account created", "data": {
                "netease": result,
                "local": {
                    "account_id": account_id,
                    "configuration": json.loads(new_user.configuration),
                    "user_information": json.loads(new_user.user_information)
                }
            }}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Database error: {str(e)}"}), 500
    else:
        return jsonify({"error": result.get('desc', 'Unknown error')}), 500

# 查询所有用户
@app.route('/users', methods=['GET'])
def get_all_users():
    # 获取所有用户信息
    try:
        users = User.query.all()
        users_data = [{
            "id": user.id,
            "account_id": user.account_id,
            "account": user.account,
            "token": user.token,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "configuration": json.loads(user.configuration) if user.configuration else {},
            "user_information": json.loads(user.user_information) if user.user_information else {}
        } for user in users]
        
        return jsonify({"count": len(users_data), "users": users_data}), 200
    except Exception as e:
        return jsonify({"error": f"Database query failed: {str(e)}"}), 500
#=======================================
#发送短信验证码方法
#=======================================
def send_sms(phone_number):
    """
    参数说明：
    - phone_number: 接收短信的手机号（必须带国际区号，如中国+86）
    文档：https://dev.yunxin.163.com/docs/短信服务/服务端API文档
    """
    
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
        response = requests.post(SEND_SMS_URL, headers=headers, data=payload)
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
# 发送短信验证码API
@app.route('/sendsms', methods=['POST'])
def handle_send_sms():
    data = request.json
    phone = data.get('phone')
    
    if not phone or len(phone) < 11:
        return jsonify({"success": False, "message": "手机号无效"})
    
    result = send_sms(phone)
    return jsonify(result)
#=======================================
#验证短信验证码方法
#=======================================

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
# 验证短信验证码API
@app.route('/verifysms', methods=['POST'])
def handle_verify_sms():
    data = request.json
    phone = data.get('phone')
    code = data.get('code')
    
    if not all([phone, code]):
        return jsonify({"valid": False, "message": "参数缺失"})
    
    result = verify_sms(phone, code)
    return jsonify(result)
#=======================================
#表情管理
#=======================================
#生成表情唯一id
def generate_object_id():
    return str(uuid.uuid4())
#上传表情
@app.route('/api/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # 从请求中获取 token
    token = request.form.get('token')
    if not token:
        return jsonify({'error': 'Missing token'}), 400

    if file:
        # 生成唯一信息
        object_id = generate_object_id()
        unique_filename = f"{object_id}.png"  # 强制保存为 .png 格式
        
        # 保存文件
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # 创建数据库记录
        image = Image(
            object_id=object_id,
            token=token,
            filename=unique_filename,
            url=f"{request.host_url}uploads/{unique_filename}"  # 拼接服务器地址
        )
        db.session.add(image)
        db.session.commit()

        return jsonify({
            'object_id': object_id,
            'token': token,
            'url': image.url
        }), 201
#根据token获取表情       
@app.route('/api/image', methods=['GET'])
def get_image():
    token = request.args.get('token')
    if not token:
        return jsonify({'error': 'Missing token'}), 400

    images = Image.query.filter_by(token=token).all()
    if not images:
        return jsonify({'error': 'No images found for this token'}), 404

    return jsonify([{
        'object_id': image.id,
        'url': image.url,
        'token': image.token
    } for image in images])
#根据object_id删除表情
@app.route('/api/image/<object_id>', methods=['DELETE'])
def delete_image(object_id):
    # 查询图片记录
    image = Image.query.get(object_id)
    if not image:
        return jsonify({'error': 'Image not found'}), 404

    # 删除文件
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image.filename))
    except FileNotFoundError:
        pass

    # 删除记录
    db.session.delete(image)
    db.session.commit()

    return jsonify({'message': 'Image deleted successfully'})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
# 根据Url添加表情
@app.route('/api/add_image_url', methods=['POST'])
def add_image_url():
    # 从请求中获取 url 和 token
    url = request.form.get('url')
    token = request.form.get('token')
    
    if not url:
        return jsonify({'error': 'Missing URL'}), 400
    if not token:
        return jsonify({'error': 'Missing token'}), 400

    # 生成唯一信息
    object_id = generate_object_id()
    filename = url.split('/')[-1]  # 使用 URL 的最后一个部分作为文件名

    # 创建数据库记录
    image = Image(
        object_id=object_id,
        token=token,
        filename=filename,
        url=url  # 直接使用传入的 URL
    )
    db.session.add(image)
    db.session.commit()

    return jsonify({
        'object_id': object_id,
        'token': token,
        'url': image.url
    }), 201
#=======================================
#获取群聊详细信息
#=======================================
def generate_headers():
    """生成网易云信 API 请求所需的头部信息"""
    # cur_time = str(int(time.time()))  # 当前时间戳
    # nonce = 'random_string'  # 随机字符串
    # check_sum_str = APP_SECRET + nonce + cur_time
    # checksum = hashlib.sha1(check_sum_str.encode('utf-8')).hexdigest()
    
    nonce = str(uuid.uuid4())
    cur_time = str(int(time.time()))
    checksum = generate_checksum(APP_SECRET, nonce, cur_time)
    return {
        'AppKey': APP_KEY,
        'Nonce': nonce,
        'CurTime': cur_time,
        'CheckSum': checksum,
        'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'
    }
#获取群聊详细信息
@app.route('/get_group_info', methods=['POST'])
def get_group_info():
    """获取群聊详细信息"""
    data = request.json
    tid = data.get('tid')
    
    if not tid:
        return jsonify({'error': '缺少群组ID'}), 400
    
    payload = {'tids': tid, 'ope': '1'}
    headers = generate_headers()
    response = requests.post(GROPUP_URL, headers=headers, data=payload)
    
    return jsonify(response.json())

# 初始化数据库
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print("初始化失败，重建数据库:", str(e))
        db.drop_all()
        db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
