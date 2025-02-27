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
    token = db.Column(db.String(32), nullable=False)  # 移除 unique=True
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

https://github.com/DIABLOSER/NetEaseService.git
        
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True)



