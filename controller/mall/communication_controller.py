"""
客户沟通控制器
"""
from flask import Blueprint, request, jsonify, session
from service.mall.communication_service import CommunicationService
from utils.auth_utils import login_required
import logging

logger = logging.getLogger(__name__)

# 创建蓝图
communication_bp = Blueprint('mall_communication', __name__, url_prefix='/api/mall/communication')

# 初始化服务
communication_service = CommunicationService()


@communication_bp.route('/admin/list', methods=['GET'])
@login_required
def get_communication_list():
    """获取客户沟通记录列表（管理员）"""
    try:
        page = request.args.get('pageNum', 1, type=int)
        limit = request.args.get('pageSize', 10, type=int)
        keyword = request.args.get('keyword', '')
        status = request.args.get('status', '')
        communication_type = request.args.get('communicationType', '')
        user_id = request.args.get('userId', '')
        
        return jsonify(communication_service.get_communication_list(page, limit, keyword, status, communication_type, user_id))
    except Exception as e:
        logger.error(f"获取客户沟通记录列表失败: {e}")
        return jsonify({"code": 500, "message": str(e)})


@communication_bp.route('/admin/<int:communication_id>', methods=['GET'])
@login_required
def get_communication_detail(communication_id):
    """获取客户沟通记录详情"""
    try:
        return jsonify(communication_service.get_communication_by_id(communication_id))
    except Exception as e:
        logger.error(f"获取客户沟通记录详情失败: {e}")
        return jsonify({"code": 500, "message": str(e)})


@communication_bp.route('/admin/create', methods=['POST'])
@login_required
def create_communication():
    """创建客户沟通记录"""
    try:
        sales_id = session.get('user_id')
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('userId'):
            return jsonify({"code": 400, "message": "客户ID不能为空"})
        if not data.get('communicationType'):
            return jsonify({"code": 400, "message": "沟通方式不能为空"})
        if not data.get('communicationTitle'):
            return jsonify({"code": 400, "message": "沟通主题不能为空"})
        if not data.get('communicationContent'):
            return jsonify({"code": 400, "message": "沟通内容不能为空"})
        
        return jsonify(communication_service.create_communication(data, sales_id))
    except Exception as e:
        logger.error(f"创建客户沟通记录失败: {e}")
        return jsonify({"code": 500, "message": str(e)})


@communication_bp.route('/admin/update', methods=['POST'])
@login_required
def update_communication():
    """更新客户沟通记录"""
    try:
        data = request.get_json()
        communication_id = data.get('id')
        
        if not communication_id:
            return jsonify({"code": 400, "message": "记录ID不能为空"})
        
        # 验证必填字段
        if not data.get('userId'):
            return jsonify({"code": 400, "message": "客户ID不能为空"})
        if not data.get('communicationType'):
            return jsonify({"code": 400, "message": "沟通方式不能为空"})
        if not data.get('communicationTitle'):
            return jsonify({"code": 400, "message": "沟通主题不能为空"})
        if not data.get('communicationContent'):
            return jsonify({"code": 400, "message": "沟通内容不能为空"})
        
        return jsonify(communication_service.update_communication(communication_id, data))
    except Exception as e:
        logger.error(f"更新客户沟通记录失败: {e}")
        return jsonify({"code": 500, "message": str(e)})


@communication_bp.route('/admin/delete', methods=['GET'])
@login_required
def delete_communication():
    """删除客户沟通记录"""
    try:
        communication_id = request.args.get('id', type=int)
        
        if not communication_id:
            return jsonify({"code": 400, "message": "记录ID不能为空"})
        
        return jsonify(communication_service.delete_communication(communication_id))
    except Exception as e:
        logger.error(f"删除客户沟通记录失败: {e}")
        return jsonify({"code": 500, "message": str(e)})


@communication_bp.route('/admin/update-status', methods=['POST'])
@login_required
def update_status():
    """更新沟通记录状态"""
    try:
        data = request.get_json()
        communication_id = data.get('id')
        status = data.get('status')
        
        if not communication_id:
            return jsonify({"code": 400, "message": "记录ID不能为空"})
        if not status:
            return jsonify({"code": 400, "message": "状态不能为空"})
        
        return jsonify(communication_service.update_status(communication_id, status))
    except Exception as e:
        logger.error(f"更新状态失败: {e}")
        return jsonify({"code": 500, "message": str(e)})


@communication_bp.route('/admin/customers', methods=['GET'])
@login_required
def get_customer_list():
    """获取客户列表（用于下拉选择）"""
    try:
        return jsonify(communication_service.get_customer_list())
    except Exception as e:
        logger.error(f"获取客户列表失败: {e}")
        return jsonify({"code": 500, "message": str(e)})


@communication_bp.route('/admin/customer/<int:user_id>/purchase-history', methods=['GET'])
@login_required
def get_customer_purchase_history(user_id):
    """获取客户购买历史"""
    try:
        return jsonify(communication_service.get_customer_purchase_history(user_id))
    except Exception as e:
        logger.error(f"获取客户购买历史失败: {e}")
        return jsonify({"code": 500, "message": str(e)})

