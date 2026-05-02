import logging
from flask import Blueprint, request, jsonify
from service.user_service import UserService
from utils.response import success, error, page_response, convert_pagination_params
from utils.auth_utils import get_current_user, admin_required

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__)
user_service = UserService()


@user_bp.route('/list', methods=['GET'])
@admin_required
def get_user_list():
    """获取用户列表"""
    try:
        page, limit = convert_pagination_params(request.args)
        keyword = request.args.get('keyword', '')
        role = request.args.get('role', '')
        status = request.args.get('status', '')
        current_user = get_current_user()
        exclude_role = 'system_admin' if current_user and current_user['role'] == 'system_admin' else None
        users, total = user_service.get_user_list(page, limit, keyword, role, status, exclude_role)
        return jsonify(page_response(users, total, page, limit))
    except Exception as e:
        logger.error(f"获取用户列表异常: {e}")
        return jsonify(error("获取用户列表失败"))


@user_bp.route('/community-options', methods=['GET'])
@admin_required
def get_community_options():
    """获取社区选项列表"""
    try:
        communities = user_service.get_community_options()
        return jsonify(success(communities, "获取社区选项成功"))
    except Exception as e:
        logger.error(f"获取社区选项异常: {e}")
        return jsonify(error("获取社区选项失败"))


@user_bp.route('/<int:user_id>', methods=['GET'])
def get_user_detail(user_id):
    """获取用户详情"""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify(error("用户未登录", 401))
        if current_user['role'] != 'system_admin' and current_user['id'] != user_id:
            return jsonify(error("无权限访问", 403))

        user = user_service.get_user_by_id(user_id)
        if user:
            return jsonify(success(user, "获取用户信息成功"))
        return jsonify(error("用户不存在"))
    except Exception as e:
        logger.error(f"获取用户详情异常: {e}")
        return jsonify(error("获取用户信息失败"))


@user_bp.route('/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """更新用户信息"""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify(error("用户未登录", 401))

        data = request.get_json() or {}
        if current_user['role'] != 'system_admin' and current_user['id'] != user_id:
            return jsonify(error("无权限修改", 403))

        if current_user['role'] != 'system_admin':
            data.pop('role', None)
            data.pop('status', None)

        result = user_service.update_user(user_id, data)
        if result:
            return jsonify(success(None, "更新成功"))
        return jsonify(error("更新失败"))
    except Exception as e:
        logger.error(f"更新用户信息异常: {e}")
        return jsonify(error("更新失败"))


@user_bp.route('/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """删除用户"""
    try:
        current_user = get_current_user()
        if current_user['id'] == user_id:
            return jsonify(error("不能删除自己的账号"))

        result = user_service.delete_user(user_id)
        if result:
            return jsonify(success(None, "删除成功"))
        return jsonify(error("删除失败"))
    except Exception as e:
        logger.error(f"删除用户异常: {e}")
        return jsonify(error("删除失败"))


@user_bp.route('/change-password', methods=['POST'])
def change_password():
    """用户修改自己的密码"""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify(error("用户未登录", 401))

        data = request.get_json() or {}
        old_password = data.get('oldPassword') or data.get('old_password')
        new_password = data.get('newPassword') or data.get('new_password')
        if not old_password or not new_password:
            return jsonify(error("原密码和新密码不能为空"))

        result = user_service.change_password(current_user['id'], old_password, new_password)
        if result:
            return jsonify(success(None, "密码修改成功"))
        return jsonify(error("原密码错误"))
    except Exception as e:
        logger.error(f"修改密码异常: {e}")
        return jsonify(error("修改密码失败"))


@user_bp.route('/reset-password/<int:user_id>', methods=['POST'])
@admin_required
def reset_user_password(user_id):
    """管理员重置用户密码"""
    try:
        current_user = get_current_user()
        if current_user['id'] == user_id:
            return jsonify(error("请使用个人中心修改自己的密码"))

        data = request.get_json() or {}
        new_password = data.get('newPassword') or data.get('new_password')
        if not new_password:
            return jsonify(error("新密码不能为空"))

        result = user_service.reset_user_password(user_id, new_password)
        if result:
            return jsonify(success(None, "密码重置成功"))
        return jsonify(error("密码重置失败"))
    except Exception as e:
        logger.error(f"重置用户密码异常: {e}")
        return jsonify(error("密码重置失败"))


@user_bp.route('/upload-avatar', methods=['POST'])
def upload_avatar():
    """上传头像"""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify(error("用户未登录", 401))

        if 'file' not in request.files:
            return jsonify(error("没有选择文件"))

        file = request.files['file']
        if file.filename == '':
            return jsonify(error("没有选择文件"))

        avatar_url = user_service.upload_avatar(current_user['id'], file)
        if avatar_url:
            return jsonify(success({'avatar_url': avatar_url}, "头像上传成功"))
        return jsonify(error("头像上传失败"))
    except Exception as e:
        logger.error(f"上传头像异常: {e}")
        return jsonify(error("头像上传失败"))


@user_bp.route('/profile', methods=['GET'])
def get_profile():
    """获取当前用户个人信息"""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify(error("用户未登录", 401))

        user_detail = user_service.get_user_by_id(current_user['id'])
        return jsonify(success(user_detail, "获取个人信息成功"))
    except Exception as e:
        logger.error(f"获取个人信息异常: {e}")
        return jsonify(error("获取个人信息失败"))


@user_bp.route('/add', methods=['POST'])
@admin_required
def add_user():
    """添加用户"""
    try:
        data = request.get_json() or {}
        required_fields = ['username', 'password', 'nickname']
        for field in required_fields:
            if not data.get(field):
                return jsonify(error(f"{field}不能为空"))

        result = user_service.add_user(data)
        if result:
            return jsonify(success(None, "添加用户成功"))
        return jsonify(error("添加用户失败，用户名可能已存在"))
    except Exception as e:
        logger.error(f"添加用户异常: {e}")
        return jsonify(error("添加用户失败"))
