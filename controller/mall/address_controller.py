"""
地址管理控制器
"""
from flask import Blueprint, request, jsonify, session
from service.mall.address_service import AddressService
from utils.auth_utils import login_required

# 创建蓝图
address_bp = Blueprint('mall_address', __name__, url_prefix='/api/mall/address')

# 初始化服务
address_service = AddressService()


@address_bp.route('/', methods=['GET'])
@login_required
def get_addresses():
    """获取用户地址列表"""
    try:
        user_id = session.get('user_id')
        return jsonify(address_service.get_addresses_by_user(user_id))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@address_bp.route('/', methods=['POST'])
@login_required
def create_address():
    """创建新地址"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['name', 'phone', 'address']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"code": 400, "message": f"{field}不能为空"})
        
        return jsonify(address_service.create_address(user_id, data))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@address_bp.route('/<int:address_id>', methods=['GET'])
@login_required
def get_address(address_id):
    """获取地址详情"""
    try:
        user_id = session.get('user_id')
        return jsonify(address_service.get_address_by_id(address_id, user_id))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@address_bp.route('/<int:address_id>', methods=['PUT'])
@login_required
def update_address(address_id):
    """更新地址"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['name', 'phone', 'address']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"code": 400, "message": f"{field}不能为空"})
        
        return jsonify(address_service.update_address(address_id, user_id, data))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@address_bp.route('/<int:address_id>', methods=['DELETE'])
@login_required
def delete_address(address_id):
    """删除地址"""
    try:
        user_id = session.get('user_id')
        return jsonify(address_service.delete_address(address_id, user_id))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@address_bp.route('/default', methods=['GET'])
@login_required
def get_default_address():
    """获取用户默认地址"""
    try:
        user_id = session.get('user_id')
        return jsonify(address_service.get_default_address(user_id))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@address_bp.route('/<int:address_id>/default', methods=['PUT'])
@login_required
def set_default_address(address_id):
    """设置默认地址"""
    try:
        user_id = session.get('user_id')
        return jsonify(address_service.set_default_address(address_id, user_id))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})
