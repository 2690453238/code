"""
新闻公告蓝图
"""
from flask import Blueprint, jsonify
from controller.announcement_controller import AnnouncementController

# 创建蓝图
announcement_bp = Blueprint('announcement', __name__)

# 后台管理接口（需要登录）
@announcement_bp.route('/admin/list', methods=['GET'])
def admin_announcement_list():
    """后台获取公告列表"""
    result = AnnouncementController.get_announcement_list()
    return jsonify(result)

@announcement_bp.route('/admin/detail', methods=['GET'])
def admin_announcement_detail():
    """后台获取公告详情"""
    result = AnnouncementController.get_announcement_detail()
    return jsonify(result)

@announcement_bp.route('/admin/create', methods=['POST'])
def admin_create_announcement():
    """后台创建公告"""
    result = AnnouncementController.create_announcement()
    return jsonify(result)

@announcement_bp.route('/admin/update', methods=['POST'])
def admin_update_announcement():
    """后台更新公告"""
    result = AnnouncementController.update_announcement()
    return jsonify(result)

@announcement_bp.route('/admin/delete', methods=['GET'])
def admin_delete_announcement():
    """后台删除公告"""
    result = AnnouncementController.delete_announcement()
    return jsonify(result)

@announcement_bp.route('/admin/toggle-status', methods=['GET'])
def admin_toggle_announcement_status():
    """后台切换公告状态"""
    result = AnnouncementController.toggle_announcement_status()
    return jsonify(result)

@announcement_bp.route('/admin/toggle-top', methods=['GET'])
def admin_toggle_announcement_top():
    """后台切换公告置顶状态"""
    result = AnnouncementController.toggle_announcement_top()
    return jsonify(result)

# 前台接口（公开访问）
@announcement_bp.route('/front/list', methods=['GET'])
def front_announcement_list():
    """前台获取公告列表"""
    result = AnnouncementController.get_front_announcements()
    return jsonify(result)

@announcement_bp.route('/front/detail', methods=['GET'])
def front_announcement_detail():
    """前台获取公告详情"""
    result = AnnouncementController.get_announcement_detail()
    return jsonify(result)
