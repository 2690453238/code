import os
import uuid
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app

logger = logging.getLogger(__name__)

def allowed_file(filename):
    """检查文件扩展名是否允许上传"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_file(file):
    """保存上传的文件"""
    if file and allowed_file(file.filename):
        # 生成安全的文件名
        filename = secure_filename(file.filename)
        # 生成唯一文件名
        unique_filename = f"{uuid.uuid4().hex}.{filename.rsplit('.', 1)[1].lower()}"
        
        # 按年月创建目录
        now = datetime.now()
        year_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(now.year))
        # month_dir = os.path.join(year_dir, f"{now.month:02d}")
        month_dir = os.path.join(current_app.config['UPLOAD_FOLDER'])
        
        # 确保目录存在
        os.makedirs(month_dir, exist_ok=True)
        
        # 保存文件
        file_path = os.path.join(month_dir, unique_filename)
        file.save(file_path)
        
        # 返回文件名（不包含完整路径）
        return unique_filename
    
    return None