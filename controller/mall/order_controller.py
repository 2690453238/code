"""
订单管理控制器
"""
from flask import Blueprint, jsonify, request, session
from service.mall.behavior_service import BehaviorService
from service.mall.order_service import OrderService
from utils.auth_utils import login_required, user_required
import logging

logger = logging.getLogger(__name__)

order_bp = Blueprint('mall_order', __name__, url_prefix='/api/mall/order')
order_service = OrderService()
behavior_service = BehaviorService()


def _get_supplier_scope():
    """获取社区团长的数据隔离范围"""
    user_role = session.get('role')
    user_id = session.get('user_id')
    if user_role == 'community_leader' and user_id:
        return user_id
    return None


def _check_write_permission():
    """检查是否有修改权限：平台运营者只读，不可修改订单"""
    if session.get('role') == 'platform_operator':
        return False
    return True


@order_bp.route('/', methods=['GET'])
@login_required
def get_orders():
    """获取用户订单列表"""
    try:
        user_id = session.get('user_id')
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        status = request.args.get('status', '')
        return jsonify(order_service.get_orders_by_user(user_id, page, limit, status))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@order_bp.route('/create', methods=['POST'])
@user_required
def create_order():
    """创建订单"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        if not data.get('items') or not data.get('addressId'):
            return jsonify({"code": 400, "message": "订单商品和收货地址不能为空"})
        return jsonify(order_service.create_order(user_id, data))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@order_bp.route('/<int:order_id>', methods=['GET'])
@login_required
def get_order_detail(order_id):
    """获取订单详情"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role')
        if user_role == 'user':
            return jsonify(order_service.get_order_by_id(order_id, user_id=user_id))
        return jsonify(
            order_service.get_order_by_id(
                order_id,
                user_id=None,
                supplier_id=_get_supplier_scope()
            )
        )
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@order_bp.route('/<int:order_id>/pay', methods=['POST'])
@user_required
def pay_order(order_id):
    """支付订单"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        payment_method = data.get('paymentMethod', 'alipay')
        result = order_service.pay_order(order_id, user_id, payment_method)

        if result.get('code') == 200:
            try:
                order_detail = order_service.get_order_by_id(order_id, user_id=user_id)
                if order_detail.get('code') == 200 and order_detail.get('data'):
                    order_data = order_detail['data']
                    if 'items' in order_data:
                        for item in order_data['items']:
                            behavior_service.record_user_behavior(
                                user_id=str(user_id),
                                item_id=str(item.get('productId')),
                                behavior_type=4,
                                item_category=str(item.get('categoryId')) if item.get('categoryId') else None,
                                user_geohash=None
                            )
                        logger.info(f"用户 {user_id} 支付订单 {order_id}，已记录购买行为")
            except Exception as behavior_error:
                logger.error(f"记录购买行为失败: {behavior_error}")

        return jsonify(result)
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@order_bp.route('/<int:order_id>/receive', methods=['PUT'])
@login_required
def confirm_receive(order_id):
    """确认收货"""
    try:
        user_id = session.get('user_id')
        return jsonify(order_service.confirm_receive(order_id, user_id))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@order_bp.route('/<int:order_id>/cancel', methods=['PUT'])
@login_required
def cancel_order(order_id):
    """取消订单"""
    try:
        user_id = session.get('user_id')
        return jsonify(order_service.cancel_order(order_id, user_id))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@order_bp.route('/stats', methods=['GET'])
@login_required
def get_order_stats():
    """获取订单统计"""
    try:
        user_id = session.get('user_id')
        return jsonify(order_service.get_order_stats(user_id))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@order_bp.route('/admin/list', methods=['GET'])
@login_required
def get_orders_admin():
    """后台获取订单列表"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        order_no = request.args.get('orderNo', '')
        username = request.args.get('username', '')
        status = request.args.get('status', '')
        start_time = request.args.get('startTime', '')
        end_time = request.args.get('endTime', '')
        return jsonify(
            order_service.get_orders_admin(
                page,
                limit,
                order_no,
                username,
                status,
                start_time,
                end_time,
                supplier_id=_get_supplier_scope()
            )
        )
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@order_bp.route('/admin/cancel-requests', methods=['GET'])
@login_required
def get_cancel_requests():
    """获取取消申请列表"""
    try:
        return jsonify(order_service.get_cancel_requests(supplier_id=_get_supplier_scope()))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@order_bp.route('/admin/<int:order_id>/approve-cancel', methods=['POST'])
@login_required
def approve_cancel_request(order_id):
    """审核取消申请"""
    try:
        if not _check_write_permission():
            return jsonify({"code": 403, "message": "平台运营者无权修改订单"})
        data = request.get_json()
        approve = data.get('approve', True)
        return jsonify(
            order_service.admin_approve_cancel(
                order_id,
                approve,
                supplier_id=_get_supplier_scope()
            )
        )
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@order_bp.route('/<int:order_id>/ship', methods=['POST'])
@login_required
def ship_order(order_id):
    """订单发货"""
    try:
        if not _check_write_permission():
            return jsonify({"code": 403, "message": "平台运营者无权修改订单"})
        data = request.get_json()
        tracking_number = data.get('trackingNumber', '')
        shipping_company = data.get('shippingCompany', '')
        logistics_info = data.get('logisticsInfo', '')

        if not tracking_number:
            return jsonify({"code": 400, "message": "物流单号不能为空"})

        return jsonify(
            order_service.ship_order(
                order_id,
                tracking_number,
                shipping_company,
                logistics_info,
                supplier_id=_get_supplier_scope()
            )
        )
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@order_bp.route('/<int:order_id>/complete', methods=['POST'])
@login_required
def complete_order(order_id):
    """完成订单"""
    try:
        if not _check_write_permission():
            return jsonify({"code": 403, "message": "平台运营者无权修改订单"})
        return jsonify(order_service.complete_order(order_id, supplier_id=_get_supplier_scope()))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@order_bp.route('/<int:order_id>/logistics', methods=['PUT'])
@login_required
def update_logistics(order_id):
    """更新物流信息"""
    try:
        if not _check_write_permission():
            return jsonify({"code": 403, "message": "平台运营者无权修改订单"})
        data = request.get_json()
        logistics_info = data.get('logisticsInfo', '')
        return jsonify(
            order_service.update_logistics_info(
                order_id,
                logistics_info,
                supplier_id=_get_supplier_scope()
            )
        )
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@order_bp.route('/<int:order_id>/review', methods=['POST'])
@login_required
def review_order_item(order_id):
    """评价订单商品"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()

        if not data.get('itemId') or not data.get('rating'):
            return jsonify({"code": 400, "message": "商品ID和评分不能为空"})

        item_id = data.get('itemId')
        rating = data.get('rating')
        content = data.get('content', '')

        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({"code": 400, "message": "评分必须在1-5之间"})

        return jsonify(order_service.review_order_item(order_id, item_id, user_id, rating, content))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@order_bp.route('/<int:order_id>', methods=['DELETE'])
@login_required
def delete_order(order_id):
    """删除订单"""
    try:
        user_id = session.get('user_id')
        return jsonify(order_service.delete_order(order_id, user_id))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})
