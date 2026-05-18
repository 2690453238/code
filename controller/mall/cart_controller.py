"""
购物车控制器
"""
from flask import Blueprint, request, jsonify, session
from service.mall.cart_service import CartService
from service.mall.behavior_service import BehaviorService
from service.mall.product_service import ProductService
from utils.auth_utils import login_required, user_required
import logging

logger = logging.getLogger(__name__)

# 创建蓝图
cart_bp = Blueprint('mall_cart', __name__, url_prefix='/api/mall/cart')

# 初始化服务
cart_service = CartService()
behavior_service = BehaviorService()
product_service = ProductService()


@cart_bp.route('/', methods=['GET'])
@user_required
def get_cart():
    """获取购物车"""
    try:
        user_id = session.get('user_id')  # 从session获取用户ID
        return jsonify(cart_service.get_cart_by_user(user_id))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@cart_bp.route('/add', methods=['POST'])
@user_required
def add_to_cart():
    """添加到购物车"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        product_id = data.get('productId')
        sku_id = data.get('skuId')
        quantity = data.get('quantity', 1)
        
        if not product_id:
            return jsonify({"code": 400, "message": "商品ID不能为空"})
        
        # 执行添加到购物车操作
        result = cart_service.add_to_cart(user_id, product_id, sku_id, quantity)
        
        # 如果添加成功，记录加购物车行为
        if result.get('code') == 200:
            try:
                # 获取商品信息以获取分类ID
                product_result = product_service.get_product_by_id(product_id)
                item_category = None
                if product_result.get('code') == 200 and product_result.get('data'):
                    item_category = str(product_result['data'].get('categoryId')) if product_result['data'].get('categoryId') else None
                
                behavior_service.record_user_behavior(
                    user_id=str(user_id),
                    item_id=str(product_id),
                    behavior_type=3,  # 加购物车行为
                    item_category=item_category,
                    user_geohash=None
                )
                logger.info(f"用户 {user_id} 将商品 {product_id} 加入购物车")
            except Exception as behavior_error:
                logger.error(f"记录加购物车行为失败: {behavior_error}")
                # 不影响主业务逻辑
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@cart_bp.route('/<int:cart_id>/quantity', methods=['PUT'])
@user_required
def update_cart_quantity(cart_id):
    """更新购物车商品数量"""
    try:
        data = request.get_json()
        quantity = data.get('quantity')
        
        if not quantity or quantity <= 0:
            return jsonify({"code": 400, "message": "数量必须大于0"})
        
        return jsonify(cart_service.update_cart_quantity(cart_id, quantity))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@cart_bp.route('/<int:cart_id>', methods=['DELETE'])
@user_required
def remove_from_cart(cart_id):
    """从购物车移除商品"""
    try:
        return jsonify(cart_service.remove_from_cart(cart_id))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@cart_bp.route('/clear', methods=['DELETE'])
@user_required
def clear_cart():
    """清空购物车"""
    try:
        user_id = session.get('user_id')
        return jsonify(cart_service.clear_cart(user_id))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@cart_bp.route('/count', methods=['GET'])
@user_required
def get_cart_count():
    """获取购物车商品数量"""
    try:
        user_id = session.get('user_id')
        return jsonify(cart_service.get_cart_count(user_id))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})
