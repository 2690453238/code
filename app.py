from flask import Flask, send_from_directory, request, redirect, url_for, session
import os
from config.config import *

# 创建Flask应用
app = Flask(__name__)

# 配置应用
app.config.from_object('config.config')

# 确保上传目录存在
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 注册蓝图
from controller.auth_controller import auth_bp
from controller.user_controller import user_bp
from controller.upload_controller import upload_bp
from controller.announcement_bp import announcement_bp
from controller.dashboard_controller import dashboard_bp
from controller.mall.behavior_controller import behavior_bp

# 商城模块蓝图
from controller.mall.category_controller import category_bp
from controller.mall.product_controller import product_bp
from controller.mall.cart_controller import cart_bp
from controller.mall.order_controller import order_bp
from controller.mall.address_controller import address_bp
from controller.mall.communication_controller import communication_bp

# 商家和管理员模块蓝图
from controller.supplier_controller import supplier_bp
from controller.admin_controller import admin_bp
from controller.analytics_controller import analytics_bp
from controller.complaint_controller import complaint_bp
from controller.smart_selection_controller import smart_selection_bp
from controller.purchase_controller import purchase_bp

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(user_bp, url_prefix='/api/user')
app.register_blueprint(upload_bp, url_prefix='/open')
app.register_blueprint(announcement_bp, url_prefix='/api/announcement')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
app.register_blueprint(behavior_bp, url_prefix='/api/mall')

# 注册商城模块蓝图
app.register_blueprint(category_bp)
app.register_blueprint(product_bp)
app.register_blueprint(cart_bp)
app.register_blueprint(order_bp)
app.register_blueprint(address_bp)
app.register_blueprint(communication_bp)

# 注册商家和管理员模块蓝图
app.register_blueprint(supplier_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(complaint_bp, url_prefix='/api/complaint')
app.register_blueprint(smart_selection_bp)
app.register_blueprint(purchase_bp)

# 页面路由分发
@app.route('/')
def index():
    """首页重定向到前台"""
    return redirect('/front/mall/mall.html')

@app.route('/login')
def login_page():
    """登录页面"""
    return send_from_directory('templates', 'login.html')

@app.route('/register')
def register_page():
    """注册页面"""
    return send_from_directory('templates', 'register.html')

@app.route('/front/<path:filename>')
def front_page(filename):
    """前台页面分发"""
    return send_from_directory('templates/front', filename)

@app.route('/admin/<path:filename>')
def admin_page(filename):
    """后台页面分发"""
    return send_from_directory('templates/admin', filename)

@app.route('/static/<path:filename>')
def static_files(filename):
    """静态文件分发"""
    return send_from_directory('static', filename)

@app.route('/upload/<path:filename>')
def upload_files(filename):
    """上传文件访问"""
    return send_from_directory('upload', filename)


if __name__ == '__main__':
    app.run(debug=DEBUG, host='0.0.0.0', port=5001)
