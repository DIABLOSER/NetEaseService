import os
import uuid
import secrets
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///images.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
db = SQLAlchemy(app)

# 创建上传目录
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

class Image(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    token = db.Column(db.String(32), unique=True, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255), nullable=False)

    def __init__(self, object_id, token, filename, url):
        self.id = object_id
        self.token = token
        self.filename = filename
        self.url = url

# 创建数据库表
with app.app_context():
    db.create_all()

def generate_object_id():
    return str(uuid.uuid4())

def generate_token():
    return secrets.token_hex(16)

# 移除 generate_token 函数

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
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        unique_filename = f"{object_id}.{ext}" if ext else object_id
        
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
        
@app.route('/api/image', methods=['GET'])
def get_image():
    token = request.args.get('token')
    if not token:
        return jsonify({'error': 'Missing token'}), 400

    image = Image.query.filter_by(token=token).first()
    if not image:
        return jsonify({'error': 'Image not found'}), 404

    return jsonify({
        'object_id': image.id,
        'url': image.url,
        'token': image.token
    })

@app.route('/api/image/<object_id>', methods=['DELETE'])
def delete_image(object_id):
    token = request.args.get('token')
    if not token:
        return jsonify({'error': 'Missing token'}), 400

    image = Image.query.get(object_id)
    if not image:
        return jsonify({'error': 'Image not found'}), 404

    if image.token != token:
        return jsonify({'error': 'Invalid token'}), 403

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True)



