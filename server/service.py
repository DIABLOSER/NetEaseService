from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests
import hashlib
import time
import uuid
import jwt
import json
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# 配置SQLite数据库
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///accounts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 更新后的用户模型
class User(db.Model):
    __tablename__ = 'users'
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

# 网易云信API配置
BASE_URL = "https://api.netease.im/nimserver/user/create.action"
APP_KEY = '9f9f680a14b27ed0b420eb79940ca0b4'
APP_SECRET = 'eb345d027e0b'

# 先定义会被路由调用的函数
def generate_checksum(secret, nonce, cur_time):
    return hashlib.sha1(f"{secret}{nonce}{cur_time}".encode()).hexdigest()

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
# 然后定义路由处理函数
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
# 新增登录路由
@app.route('/login', methods=['POST'])
def handle_login():
    # 验证请求数据
    if not request.json or 'username' not in request.json or 'token' not in request.json:
        return jsonify({"error": "Missing username or token"}), 400

    username = request.json['username']
    input_token = request.json['token']

    # 查询数据库（支持account_id或account登录）
    user = User.query.filter(
        # 使用账号Id+token登录
        (User.account_id == username) & (User.token == input_token)
    ).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    # 验证token（生产环境应使用哈希验证）
    if user.token != input_token:
        return jsonify({"error": "Invalid credentials"}), 401

    # 生成JWT令牌（有效期1小时）
    token = jwt.encode({
        'sub': user.account_id,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=1)
    }, app.config['SECRET_KEY'], algorithm='HS256')

    # 返回该用户的所有数据
    user_data = {
        "id": user.id,
        "account_id": user.account_id,
        "account": user.account,
        "token": user.token,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "configuration": json.loads(user.configuration) if user.configuration else {},
        "user_information": json.loads(user.user_information) if user.user_information else {}
    }

    return jsonify({
        "message": "Login successful",
        "access_token": token,
        "user": user_data
    }), 200
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