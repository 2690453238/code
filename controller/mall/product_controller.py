"""
商品控制器
"""
from flask import Blueprint, request, jsonify, session
from service.mall.product_service_fixed import ProductService
from service.mall.behavior_service import BehaviorService
from utils.auth_utils import get_current_user
import logging

logger = logging.getLogger(__name__)

# 创建蓝图
product_bp = Blueprint('mall_product', __name__, url_prefix='/api/mall/product')

# 初始化服务
product_service = ProductService()
behavior_service = BehaviorService()


@product_bp.route('/list', methods=['GET'])
def get_product_list():
    """获取商品列表"""
    try:
        category_id = request.args.get('categoryId', type=int)
        status = request.args.get('status', type=int)  # 不设置默认值，允许查询所有状态
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        keyword = request.args.get('keyword', type=str)
        sort_type = request.args.get('sortType', 'default', type=str)
        
        current_user = get_current_user()
        return jsonify(product_service.get_products(category_id, status, page, limit, keyword, sort_type, current_user))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@product_bp.route('/<int:product_id>', methods=['GET'])
def get_product_detail(product_id):
    """获取商品详情"""
    try:
        # 获取商品详情
        result = product_service.get_product_by_id(product_id)
        
        # 如果获取成功且用户已登录，记录浏览行为
        if result.get('code') == 200 and result.get('data'):
            current_user = get_current_user()
            if current_user:
                try:
                    product_data = result['data']
                    behavior_service.record_user_behavior(
                        user_id=str(current_user['id']),
                        item_id=str(product_id),
                        behavior_type=1,  # 浏览行为
                        item_category=str(product_data.get('categoryId')) if product_data.get('categoryId') else None,
                        user_geohash=None
                    )
                    logger.info(f"用户 {current_user['id']} 浏览商品 {product_id}")
                except Exception as behavior_error:
                    logger.error(f"记录浏览行为失败: {behavior_error}")
                    # 不影响主业务逻辑，继续返回商品详情
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@product_bp.route('/hot', methods=['GET'])
def get_hot_products():
    """获取热门商品"""
    try:
        limit = request.args.get('limit', 10, type=int)
        return jsonify(product_service.get_hot_products(limit))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@product_bp.route('/new', methods=['GET'])
def get_new_products():
    """获取新品商品"""
    try:
        limit = request.args.get('limit', 10, type=int)
        return jsonify(product_service.get_new_products(limit))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@product_bp.route('/<int:product_id>/reviews', methods=['GET'])
def get_product_reviews(product_id):
    """获取商品评价列表"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        return jsonify(product_service.get_product_reviews(product_id, page, limit))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@product_bp.route('/<int:product_id>/reviews/stats', methods=['GET'])
def get_product_review_stats(product_id):
    """获取商品评价统计信息"""
    try:
        return jsonify(product_service.get_product_review_stats(product_id))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@product_bp.route('/<int:product_id>/recommendations', methods=['GET'])
def get_product_recommendations(product_id):
    """获取关联商品推荐"""
    try:
        limit = request.args.get('limit', 6, type=int)
        return jsonify(product_service.get_related_recommendations(product_id, limit))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@product_bp.route('/', methods=['POST'])
def create_product():
    """创建商品"""
    try:
        data = request.get_json()
        current_user = get_current_user()
        return jsonify(product_service.create_product(data, current_user))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@product_bp.route('/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """更新商品"""
    try:
        data = request.get_json()
        current_user = get_current_user()
        return jsonify(product_service.update_product(product_id, data, current_user))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@product_bp.route('/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """删除商品"""
    try:
        current_user = get_current_user()
        return jsonify(product_service.delete_product(product_id, current_user))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@product_bp.route('/<int:product_id>/status', methods=['PUT'])
def toggle_product_status(product_id):
    """切换商品状态"""
    try:
        data = request.get_json()
        status = data.get('status')
        current_user = get_current_user()
        return jsonify(product_service.update_product_status(product_id, status, current_user))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@product_bp.route('/batch', methods=['DELETE'])
def batch_delete_products():
    """批量删除商品"""
    try:
        data = request.get_json()
        product_ids = data.get('ids', [])
        current_user = get_current_user()
        return jsonify(product_service.batch_delete_products(product_ids, current_user))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})
