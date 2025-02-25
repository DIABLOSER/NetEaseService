from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import shutil
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)

# 配置数据库，SQLite存储
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///images.db'  # 使用SQLite数据库
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 禁用对象修改追踪
db = SQLAlchemy(app)

# 配置上传文件夹和支持的文件类型
UPLOAD_FOLDER = './emoji_images'  # 存储上传图片的文件夹
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}  # 支持的图片格式

# 确保上传文件夹存在
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 创建图片信息表
class Image(db.Model):
    __tablename__ = 'images'
    id = db.Column(db.String(36), primary_key=True, default=str(uuid.uuid4()))  # objectId
    url = db.Column(db.String(200), nullable=False)
    token = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f"<Image {self.id}>"

# 使用 app_context 来初始化数据库表
with app.app_context():
    db.create_all()  # 创建数据库表

# 检查文件格式是否允许
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 上传图片并保存数据库记录
@app.route('/upload', methods=['POST'])
def upload_image():
    token = request.form.get('token')
    file = request.files.get('file')  # 获取上传的文件

    if not token or not file:
        return jsonify({'error': 'Missing token or file'}), 400

    try:
        filename = secure_filename(file.filename)

        # 检查文件格式
        if not allowed_file(filename):
            return jsonify({'error': 'File type not allowed'}), 400

        # 保存文件到上传文件夹
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        # 创建新的Image对象
        image_record = Image(url=file_path, token=token)

        # 保存记录到数据库
        db.session.add(image_record)
        db.session.commit()

        return jsonify({
            'message': 'Image uploaded successfully', 
            'file_path': file_path,
            'objectId': image_record.id
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 根据 objectId 删除记录
@app.route('/delete', methods=['DELETE'])
def delete_image():
    object_id = request.args.get('objectId')

    if not object_id:
        return jsonify({'error': 'Missing objectId'}), 400

    # 查询数据库，删除指定 objectId 的记录
    image_record = Image.query.filter_by(id=object_id).first()

    if not image_record:
        return jsonify({'error': 'Image record not found'}), 404

    try:
        # 删除文件
        if os.path.exists(image_record.url):
            os.remove(image_record.url)

        # 删除数据库中的记录
        db.session.delete(image_record)
        db.session.commit()

        return jsonify({'message': 'Image deleted successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 根据token查询图片
@app.route('/query', methods=['GET'])
def get_images_by_token():
    token = request.args.get('token')

    if not token:
        return jsonify({'error': 'Missing token'}), 400

    # 查询该token对应的所有图片记录
    images = Image.query.filter_by(token=token).all()
    
    if not images:
        return jsonify({'error': 'No images found for this token'}), 404

    image_urls = [image.url for image in images]

    return jsonify({'token': token, 'images': image_urls}), 200

if __name__ == '__main__':
     app.run(debug=True, host='0.0.0.0', port=5003)



