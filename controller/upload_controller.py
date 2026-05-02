from flask import Blueprint, request, jsonify
from utils.file_utils import allowed_file, save_file
from utils.response import success, error
import logging
import os

logger = logging.getLogger(__name__)

# 创建上传蓝图
upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """统一文件上传接口"""
    try:
        if 'file' not in request.files:
            return jsonify(error("没有选择文件"))
        
        file = request.files['file']
        if file.filename == '':
            return jsonify(error("没有选择文件"))
        
        if not allowed_file(file.filename):
            return jsonify(error("不支持的文件类型"))
        
        # 保存文件
        filename = save_file(file)
        if filename:
            file_url = f"/upload/{filename}"
            logger.info(f"文件上传成功: {filename}")
            return jsonify(success({
                'filename': filename,
                'url': file_url
            }, "文件上传成功"))
        else:
            return jsonify(error("文件上传失败"))
            
    except Exception as e:
        logger.error(f"文件上传异常: {e}")
        return jsonify(error("文件上传失败"))

@upload_bp.route('/delete', methods=['POST'])
def delete_file():
    """删除文件"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify(error("文件名不能为空"))
        
        # 构建文件路径
        file_path = os.path.join('upload', filename)
        
        # 检查文件是否存在
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"文件删除成功: {filename}")
            return jsonify(success(None, "文件删除成功"))
        else:
            return jsonify(error("文件不存在"))
            
    except Exception as e:
        logger.error(f"文件删除异常: {e}")
        return jsonify(error("文件删除失败"))
