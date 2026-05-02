"""
系统管理员控制器
处理系统管理员对社区团长账户的管理操作
"""
from flask import Blueprint, request, jsonify
from service.admin_service import AdminService
from utils.auth_utils import get_current_user
from utils.response import success, error, page_response

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def check_admin_permission():
    """检查是否为系统管理员"""
    user_info = get_current_user()
    if not user_info:
        return False, None
    if user_info.get('role') != 'system_admin':
        return False, user_info
    return True, user_info


@admin_bp.route('/suppliers', methods=['GET'])
def get_suppliers():
    """获取社区团长列表"""
    has_permission, _ = check_admin_permission()
    if not has_permission:
        return jsonify(error('无权访问', 403))

    try:
        page_num = request.args.get('pageNum', 1, type=int)
        page_size = request.args.get('pageSize', 10, type=int)
        keyword = request.args.get('keyword', '', type=str)
        supplier_status = request.args.get('supplierStatus', '', type=str)

        result = AdminService.get_suppliers(page_num, page_size, keyword, supplier_status)
        return jsonify(page_response(result['rows'], result['total'], result['pageNum'], result['pageSize']))
    except Exception as e:
        print(f"获取社区团长列表失败: {str(e)}")
        return jsonify(error(f'获取社区团长列表失败: {str(e)}'))


@admin_bp.route('/suppliers', methods=['POST'])
def create_supplier():
    """创建社区团长"""
    has_permission, _ = check_admin_permission()
    if not has_permission:
        return jsonify(error('无权访问', 403))

    try:
        data = request.get_json() or {}
        required_fields = ['username', 'password', 'supplierName', 'supplierCode',
                           'supplierContact', 'supplierContactPhone']
        for field in required_fields:
            if not data.get(field):
                return jsonify(error(f'{field}不能为空'))

        data['role'] = 'community_leader'
        result = AdminService.create_supplier(data)
        if result['success']:
            return jsonify(success({'id': result['id']}, '创建成功'))
        return jsonify(error(result['message']))
    except Exception as e:
        print(f"创建社区团长失败: {str(e)}")
        return jsonify(error(f'创建社区团长失败: {str(e)}'))


@admin_bp.route('/suppliers/<int:supplier_id>', methods=['PUT'])
def update_supplier(supplier_id):
    """更新社区团长信息"""
    has_permission, _ = check_admin_permission()
    if not has_permission:
        return jsonify(error('无权访问', 403))

    try:
        data = request.get_json() or {}
        result = AdminService.update_supplier(supplier_id, data)
        if result['success']:
            return jsonify(success(None, '更新成功'))
        return jsonify(error(result['message']))
    except Exception as e:
        print(f"更新社区团长失败: {str(e)}")
        return jsonify(error(f'更新社区团长失败: {str(e)}'))


@admin_bp.route('/suppliers/<int:supplier_id>', methods=['DELETE'])
def delete_supplier(supplier_id):
    """删除社区团长"""
    has_permission, _ = check_admin_permission()
    if not has_permission:
        return jsonify(error('无权访问', 403))

    try:
        result = AdminService.delete_supplier(supplier_id)
        if result['success']:
            return jsonify(success(None, '删除成功'))
        return jsonify(error(result['message']))
    except Exception as e:
        print(f"删除社区团长失败: {str(e)}")
        return jsonify(error(f'删除社区团长失败: {str(e)}'))


@admin_bp.route('/suppliers/<int:supplier_id>/approve', methods=['PUT'])
def approve_supplier(supplier_id):
    """审核通过社区团长"""
    has_permission, _ = check_admin_permission()
    if not has_permission:
        return jsonify(error('无权访问', 403))

    try:
        result = AdminService.update_supplier_status(supplier_id, 'approved')
        if result['success']:
            return jsonify(success(None, '审核通过'))
        return jsonify(error(result['message']))
    except Exception as e:
        print(f"审核失败: {str(e)}")
        return jsonify(error(f'审核失败: {str(e)}'))


@admin_bp.route('/suppliers/<int:supplier_id>/reject', methods=['PUT'])
def reject_supplier(supplier_id):
    """拒绝社区团长审核"""
    has_permission, _ = check_admin_permission()
    if not has_permission:
        return jsonify(error('无权访问', 403))

    try:
        result = AdminService.update_supplier_status(supplier_id, 'rejected')
        if result['success']:
            return jsonify(success(None, '已拒绝'))
        return jsonify(error(result['message']))
    except Exception as e:
        print(f"操作失败: {str(e)}")
        return jsonify(error(f'操作失败: {str(e)}'))


@admin_bp.route('/suppliers/<int:supplier_id>/status', methods=['PUT'])
def toggle_supplier_account_status(supplier_id):
    """切换社区团长账号状态"""
    has_permission, _ = check_admin_permission()
    if not has_permission:
        return jsonify(error('无权访问', 403))

    try:
        data = request.get_json() or {}
        status = data.get('status')
        if status not in ['active', 'locked']:
            return jsonify(error('状态参数错误'))

        result = AdminService.update_account_status(supplier_id, status)
        if result['success']:
            return jsonify(success(None, '操作成功'))
        return jsonify(error(result['message']))
    except Exception as e:
        print(f"操作失败: {str(e)}")
        return jsonify(error(f'操作失败: {str(e)}'))
