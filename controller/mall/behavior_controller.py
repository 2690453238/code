from flask import Blueprint, request, jsonify, session
from service.mall.behavior_service import BehaviorService
from utils.response import success, error
from utils.auth_utils import get_current_user
import logging

logger = logging.getLogger(__name__)

# 创建用户行为蓝图
behavior_bp = Blueprint('mall_behavior', __name__)

# 初始化行为服务
behavior_service = BehaviorService()

@behavior_bp.route('/behavior/stats/<user_id>', methods=['GET'])
def get_user_behavior_stats(user_id):
    """获取用户行为统计"""
    try:
        # 检查权限（只能查看自己的统计或管理员可以查看所有）
        current_user = get_current_user()
        if not current_user:
            return jsonify(error("用户未登录"))
        
        if str(current_user['id']) != str(user_id) and current_user.get('role') not in ['system_admin', 'platform_operator']:
            return jsonify(error("无权限查看该用户统计"))
        
        # 获取统计数据
        stats = behavior_service.get_user_behavior_stats(user_id)
        
        return jsonify(success(stats, "获取统计数据成功"))
        
    except Exception as e:
        logger.error(f"获取用户行为统计异常: {e}")
        return jsonify(error("获取统计数据失败，请稍后重试"))

@behavior_bp.route('/behavior/history/<user_id>', methods=['GET'])
def get_user_behavior_history(user_id):
    """获取用户行为历史"""
    try:
        # 检查权限
        current_user = get_current_user()
        if not current_user:
            return jsonify(error("用户未登录"))
        
        if str(current_user['id']) != str(user_id) and current_user.get('role') not in ['system_admin', 'platform_operator']:
            return jsonify(error("无权限查看该用户历史"))
        
        # 获取分页参数
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        behavior_type = request.args.get('behavior_type')
        
        # 获取历史数据
        history = behavior_service.get_user_behavior_history(
            user_id=user_id,
            page=page,
            limit=limit,
            behavior_type=behavior_type
        )
        
        return jsonify(success(history, "获取历史数据成功"))
        
    except Exception as e:
        logger.error(f"获取用户行为历史异常: {e}")
        return jsonify(error("获取历史数据失败，请稍后重试"))
