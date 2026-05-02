import os
import pymysql

# 应用配置
DEBUG = True
SECRET_KEY = 'your-secret-key-here'

# 数据库配置
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': '0_80421shequtuangou',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# 上传文件配置
UPLOAD_FOLDER = 'upload'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# 会话配置
PERMANENT_SESSION_LIFETIME = 86400  # 24小时