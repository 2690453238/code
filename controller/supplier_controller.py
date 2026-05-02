"""
社区团长控制器，处理社区团长相关的 HTTP 请求
"""
from flask import Blueprint, request, jsonify
from service.supplier_service import SupplierService
from utils.auth_utils import get_current_user
from utils.response import success, error, page_response

supplier_bp = Blueprint('supplier', __name__, url_prefix='/api/supplier')


def check_supplier_permission():
    """检查是否为社区团长或具备平台管理权限"""
    user_info = get_current_user()
    if not user_info:
        return False, None

    if user_info.get('role') not in ['community_leader', 'system_admin', 'platform_operator']:
        return False, None

    return True, user_info


@supplier_bp.route('/stats', methods=['GET'])
def get_stats():
    """获取社区团长统计数据"""
    has_permission, user_info = check_supplier_permission()
    if not has_permission:
        return jsonify(error('无权访问', 403))

    try:
        stats = SupplierService.get_supplier_stats(user_info)
        return jsonify(success(stats))
    except Exception as e:
        return jsonify(error(f'获取统计数据失败: {str(e)}'))


@supplier_bp.route('/top-products', methods=['GET'])
def get_top_products():
    """获取热销商品 TOP 列表"""
    has_permission, user_info = check_supplier_permission()
    if not has_permission:
        return jsonify(error('无权访问', 403))

    try:
        limit = request.args.get('limit', 10, type=int)
        products = SupplierService.get_top_products(user_info, limit)
        return jsonify(success(products))
    except Exception as e:
        return jsonify(error(f'获取热销商品失败: {str(e)}'))


@supplier_bp.route('/order-trend', methods=['GET'])
def get_order_trend():
    """获取近期订单趋势"""
    has_permission, user_info = check_supplier_permission()
    if not has_permission:
        return jsonify(error('无权访问', 403))

    try:
        days = request.args.get('days', 30, type=int)
        trend = SupplierService.get_order_trend(user_info, days)
        return jsonify(success(trend))
    except Exception as e:
        return jsonify(error(f'获取订单趋势失败: {str(e)}'))


@supplier_bp.route('/products', methods=['GET'])
def get_products():
    """获取社区团长商品列表"""
    has_permission, user_info = check_supplier_permission()
    if not has_permission:
        return jsonify(error('无权访问', 403))

    try:
        page_num = request.args.get('pageNum', 1, type=int)
        page_size = request.args.get('pageSize', 10, type=int)
        keyword = request.args.get('keyword', '', type=str)
        status = request.args.get('status', type=int)
        category_id = request.args.get('categoryId', type=int)
        result = SupplierService.get_supplier_products(user_info, page_num, page_size, keyword, status, category_id)
        return jsonify(page_response(result['rows'], result['total'], result['pageNum'], result['pageSize']))
    except Exception as e:
        return jsonify(error(f'获取商品列表失败: {str(e)}'))


@supplier_bp.route('/orders', methods=['GET'])
def get_orders():
    """获取社区团长订单列表"""
    has_permission, user_info = check_supplier_permission()
    if not has_permission:
        return jsonify(error('无权访问', 403))

    try:
        page_num = request.args.get('pageNum', 1, type=int)
        page_size = request.args.get('pageSize', 10, type=int)
        status = request.args.get('status', type=str)
        result = SupplierService.get_supplier_orders(user_info, page_num, page_size, status)
        return jsonify(page_response(result['rows'], result['total'], result['pageNum'], result['pageSize']))
    except Exception as e:
        return jsonify(error(f'获取订单列表失败: {str(e)}'))


@supplier_bp.route('/product/check-permission/<int:product_id>', methods=['GET'])
def check_product_permission(product_id):
    """检查商品操作权限"""
    has_permission, user_info = check_supplier_permission()
    if not has_permission:
        return jsonify(error('无权访问', 403))

    try:
        has_perm = SupplierService.check_product_permission(user_info, product_id)
        return jsonify(success({'hasPermission': has_perm}))
    except Exception as e:
        return jsonify(error(f'检查权限失败: {str(e)}'))
