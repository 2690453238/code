"""
仪表盘控制器
处理仪表盘相关的API请求
"""
from flask import Blueprint, jsonify, request
from service.dashboard_service import DashboardService
from utils.response import success, error

# 创建蓝图
dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/overview', methods=['GET'])
def get_dashboard_overview():
    """获取仪表盘总览数据"""
    try:
        data = DashboardService.get_dashboard_overview()
        return jsonify(success(data))
    except Exception as e:
        return jsonify(error(f"获取仪表盘数据失败: {str(e)}"))

@dashboard_bp.route('/user-stats', methods=['GET'])
def get_user_statistics():
    """获取用户统计数据"""
    try:
        data = DashboardService.get_user_statistics()
        return jsonify(success(data))
    except Exception as e:
        return jsonify(error(f"获取用户统计失败: {str(e)}"))

@dashboard_bp.route('/user-trend', methods=['GET'])
def get_user_trend():
    """获取用户注册趋势数据"""
    try:
        days = request.args.get('days', 30, type=int)
        data = DashboardService.get_user_trend_data(days)
        return jsonify(success(data))
    except Exception as e:
        return jsonify(error(f"获取用户趋势数据失败: {str(e)}"))

@dashboard_bp.route('/role-distribution', methods=['GET'])
def get_role_distribution():
    """获取用户角色分布数据"""
    try:
        data = DashboardService.get_role_distribution()
        return jsonify(success(data))
    except Exception as e:
        return jsonify(error(f"获取角色分布数据失败: {str(e)}"))

@dashboard_bp.route('/recent-activities', methods=['GET'])
def get_recent_activities():
    """获取最近活动数据"""
    try:
        limit = request.args.get('limit', 10, type=int)
        data = DashboardService.get_recent_activities(limit)
        return jsonify(success(data))
    except Exception as e:
        return jsonify(error(f"获取最近活动数据失败: {str(e)}"))
