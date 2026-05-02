"""
商品分类控制器
"""
from flask import Blueprint, request, jsonify
from service.mall.category_service import CategoryService

# 创建蓝图
category_bp = Blueprint('mall_category', __name__, url_prefix='/api/mall/category')

# 初始化服务
category_service = CategoryService()


@category_bp.route('/list', methods=['GET'])
def get_category_list():
    """获取分类列表"""
    try:
        return jsonify(category_service.get_all_categories())
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@category_bp.route('/tree', methods=['GET'])
def get_category_tree():
    """获取分类树"""
    try:
        return jsonify(category_service.get_category_tree())
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@category_bp.route('/<int:category_id>', methods=['GET'])
def get_category_detail(category_id):
    """获取分类详情"""
    try:
        return jsonify(category_service.get_category_by_id(category_id))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@category_bp.route('/', methods=['POST'])
def create_category():
    """创建分类"""
    try:
        data = request.get_json()
        name = data.get('name')
        parent_id = data.get('parentId', 0)
        sort = data.get('sort', 0)
        
        return jsonify(category_service.create_category(name, parent_id, sort))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@category_bp.route('/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    """更新分类"""
    try:
        data = request.get_json()
        name = data.get('name')
        sort = data.get('sort')
        
        return jsonify(category_service.update_category(category_id, name, sort))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})


@category_bp.route('/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    """删除分类"""
    try:
        return jsonify(category_service.delete_category(category_id))
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)})
