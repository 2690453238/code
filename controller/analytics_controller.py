"""数据分析控制器"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from flask import Blueprint, jsonify, request, session

from service.analytics_service_fixed import AnalyticsService
from service.sales_forecast_service import get_forecast_service
from utils.auth_utils import login_required

logger = logging.getLogger(__name__)

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")
analytics_service = AnalyticsService()
sales_forecast_service = get_forecast_service()

GLOBAL_ANALYTICS_ROLES = ["system_admin", "platform_operator", "admin"]
COMMUNITY_ANALYTICS_ROLES = ["community_leader", "supplier"] + GLOBAL_ANALYTICS_ROLES


def _json_error(message: str, code: int = 500) -> Any:
    """返回统一错误响应"""
    return jsonify({"code": code, "message": message, "data": None})


def _get_current_role() -> str:
    """获取当前登录角色"""
    return session.get("role") or session.get("user_role", "")


def _has_global_permission() -> bool:
    """是否具备全局分析权限"""
    return _get_current_role() in GLOBAL_ANALYTICS_ROLES


def _has_community_permission() -> bool:
    """是否具备社区分析权限"""
    return _get_current_role() in COMMUNITY_ANALYTICS_ROLES


def _get_supplier_id() -> Optional[int]:
    """获取社区团长范围ID"""
    user_id = session.get("user_id")
    user_role = _get_current_role()
    if user_role in ["community_leader", "supplier"] and user_id:
        return int(user_id)

    supplier_id = request.args.get("supplierId", type=int)
    if supplier_id is not None:
        return supplier_id if user_role in GLOBAL_ANALYTICS_ROLES else None
    return None


def _resolve_forecast_supplier_id() -> Optional[int]:
    """解析预测范围ID"""
    if _has_global_permission():
        return request.args.get("supplierId", default=None, type=int)
    return _get_supplier_id()


def _execute_with_guard(
    permission_checker: Callable[[], bool],
    action: Callable[[], Dict[str, Any]],
    error_message: str,
) -> Any:
    """统一执行受权限保护的接口"""
    try:
        if not permission_checker():
            return _json_error("权限不足", 403)
        return jsonify(action())
    except Exception as exc:
        logger.error("%s: %s", error_message, exc)
        return _json_error(str(exc))


@analytics_bp.route("/market/overview", methods=["GET"])
@login_required
def get_market_overview() -> Any:
    return _execute_with_guard(_has_global_permission, analytics_service.get_market_overview, "获取市场概览失败")


@analytics_bp.route("/market/price-trend", methods=["GET"])
@login_required
def get_price_trend() -> Any:
    return _execute_with_guard(
        _has_global_permission,
        lambda: analytics_service.get_price_trend(request.args.get("days", 30, type=int)),
        "获取价格趋势失败",
    )


@analytics_bp.route("/market/hot-products", methods=["GET"])
@login_required
def get_hot_products() -> Any:
    return _execute_with_guard(
        _has_global_permission,
        lambda: analytics_service.get_hot_products(request.args.get("limit", 10, type=int)),
        "获取热门商品失败",
    )


@analytics_bp.route("/market/category-distribution", methods=["GET"])
@login_required
def get_category_distribution() -> Any:
    return _execute_with_guard(
        _has_global_permission,
        analytics_service.get_category_distribution,
        "获取分类分布失败",
    )


@analytics_bp.route("/sales/trend", methods=["GET"])
@login_required
def get_sales_trend() -> Any:
    return _execute_with_guard(
        _has_global_permission,
        lambda: analytics_service.get_sales_trend(request.args.get("days", 30, type=int)),
        "获取销售趋势失败",
    )


@analytics_bp.route("/alerts/inventory", methods=["GET"])
@login_required
def get_inventory_alerts() -> Any:
    return _execute_with_guard(_has_global_permission, analytics_service.get_inventory_alerts, "获取库存预警失败")


@analytics_bp.route("/alerts/price", methods=["GET"])
@login_required
def get_price_alerts() -> Any:
    return _execute_with_guard(_has_global_permission, analytics_service.get_price_alerts, "获取价格预警失败")


@analytics_bp.route("/forecast/demand", methods=["GET"])
@login_required
def get_demand_forecast() -> Any:
    return _execute_with_guard(
        _has_global_permission,
        lambda: analytics_service.get_demand_forecast(request.args.get("days", 7, type=int)),
        "获取需求预测失败",
    )


@analytics_bp.route("/analysis/product-association", methods=["GET"])
@login_required
def get_product_association() -> Any:
    return _execute_with_guard(
        _has_global_permission,
        analytics_service.get_product_association,
        "获取商品关联分析失败",
    )


@analytics_bp.route("/analysis/regional-sales", methods=["GET"])
@login_required
def get_regional_sales() -> Any:
    return _execute_with_guard(_has_global_permission, analytics_service.get_regional_sales, "获取区域销售失败")


@analytics_bp.route("/report/product-price", methods=["GET"])
@login_required
def get_product_price_distribution() -> Any:
    return _execute_with_guard(
        _has_global_permission,
        analytics_service.get_product_price_distribution,
        "获取商品价格分布失败",
    )


@analytics_bp.route("/report/review-summary", methods=["GET"])
@login_required
def get_review_summary() -> Any:
    return _execute_with_guard(_has_global_permission, analytics_service.get_review_summary, "获取评价汇总失败")


@analytics_bp.route("/report/category-competition", methods=["GET"])
@login_required
def get_category_competition() -> Any:
    return _execute_with_guard(
        _has_global_permission,
        analytics_service.get_category_competition,
        "获取品类竞争分析失败",
    )


@analytics_bp.route("/supplier/overview", methods=["GET"])
@login_required
def supplier_overview() -> Any:
    def action() -> Dict[str, Any]:
        supplier_id = _get_supplier_id()
        if supplier_id is None:
            return {"code": 401, "message": "请先登录或指定社区团长", "data": None}
        return analytics_service.supplier_overview(supplier_id)

    return _execute_with_guard(_has_community_permission, action, "获取社区概览失败")


@analytics_bp.route("/supplier/sales-trend", methods=["GET"])
@login_required
def supplier_sales_trend() -> Any:
    def action() -> Dict[str, Any]:
        supplier_id = _get_supplier_id()
        if supplier_id is None:
            return {"code": 401, "message": "请先登录或指定社区团长", "data": None}
        return analytics_service.supplier_sales_trend(supplier_id, request.args.get("days", 30, type=int))

    return _execute_with_guard(_has_community_permission, action, "获取社区销售趋势失败")


@analytics_bp.route("/supplier/product-rank", methods=["GET"])
@login_required
def supplier_product_rank() -> Any:
    def action() -> Dict[str, Any]:
        supplier_id = _get_supplier_id()
        if supplier_id is None:
            return {"code": 401, "message": "请先登录或指定社区团长", "data": None}
        return analytics_service.supplier_product_rank(supplier_id, request.args.get("limit", 10, type=int))

    return _execute_with_guard(_has_community_permission, action, "获取社区商品排行失败")


@analytics_bp.route("/supplier/category-sales", methods=["GET"])
@login_required
def supplier_category_sales() -> Any:
    def action() -> Dict[str, Any]:
        supplier_id = _get_supplier_id()
        if supplier_id is None:
            return {"code": 401, "message": "请先登录或指定社区团长", "data": None}
        return analytics_service.supplier_category_sales(supplier_id)

    return _execute_with_guard(_has_community_permission, action, "获取社区品类销售失败")


@analytics_bp.route("/supplier/review-analysis", methods=["GET"])
@login_required
def supplier_review_analysis() -> Any:
    def action() -> Dict[str, Any]:
        supplier_id = _get_supplier_id()
        if supplier_id is None:
            return {"code": 401, "message": "请先登录或指定社区团长", "data": None}
        return analytics_service.supplier_review_analysis(supplier_id)

    return _execute_with_guard(_has_community_permission, action, "获取社区评价分析失败")


@analytics_bp.route("/supplier/inventory-alert", methods=["GET"])
@login_required
def supplier_inventory_alert() -> Any:
    def action() -> Dict[str, Any]:
        supplier_id = _get_supplier_id()
        if supplier_id is None:
            return {"code": 401, "message": "请先登录或指定社区团长", "data": None}
        return analytics_service.supplier_inventory_alert(supplier_id)

    return _execute_with_guard(_has_community_permission, action, "获取社区库存预警失败")


@analytics_bp.route("/forecast/sales/train", methods=["POST"])
@login_required
def train_sales_forecast_model() -> Any:
    return _execute_with_guard(
        _has_community_permission,
        lambda: sales_forecast_service.train_model(
            _resolve_forecast_supplier_id(),
            request.args.get("forecastDays", 7, type=int),
            request.args.get("testDays", 14, type=int),
        ),
        "训练销量预测模型失败",
    )


@analytics_bp.route("/forecast/sales/evaluation", methods=["GET"])
@login_required
def get_sales_forecast_evaluation() -> Any:
    return _execute_with_guard(
        _has_community_permission,
        lambda: sales_forecast_service.get_evaluation(
            _resolve_forecast_supplier_id(),
            request.args.get("forecastDays", 7, type=int),
            request.args.get("testDays", 14, type=int),
        ),
        "获取销量预测评估失败",
    )


@analytics_bp.route("/forecast/sales/batch", methods=["GET"])
@login_required
def batch_predict_sales() -> Any:
    return _execute_with_guard(
        _has_community_permission,
        lambda: sales_forecast_service.batch_predict(
            _resolve_forecast_supplier_id(),
            request.args.get("forecastDays", 7, type=int),
            request.args.get("testDays", 14, type=int),
            request.args.get("productId", default=None, type=int),
        ),
        "执行批量销量预测失败",
    )


@analytics_bp.route("/forecast/sales/dashboard", methods=["GET"])
@login_required
def get_sales_forecast_dashboard() -> Any:
    return _execute_with_guard(
        _has_community_permission,
        lambda: sales_forecast_service.get_dashboard(
            _resolve_forecast_supplier_id(),
            request.args.get("forecastDays", 7, type=int),
            request.args.get("testDays", 14, type=int),
            request.args.get("trendDays", 30, type=int),
        ),
        "获取销量预测看板失败",
    )
