"""智能选品控制器"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from flask import Blueprint, jsonify, request, session

from service.smart_selection_service import SmartSelectionService
from utils.auth_utils import login_required
from utils.response import error

logger = logging.getLogger(__name__)

smart_selection_bp = Blueprint(
    "smart_selection", __name__, url_prefix="/api/smart-selection"
)
service = SmartSelectionService()

GLOBAL_ANALYTICS_ROLES = ["system_admin", "platform_operator", "admin"]
COMMUNITY_ANALYTICS_ROLES = ["community_leader", "supplier"] + GLOBAL_ANALYTICS_ROLES


def _has_community_permission() -> bool:
    return session.get("role") in COMMUNITY_ANALYTICS_ROLES


def _resolve_supplier_id() -> Optional[int]:
    """解析数据范围：团长只看自己，管理员可指定"""
    role = session.get("role")
    if role in GLOBAL_ANALYTICS_ROLES:
        return request.args.get("supplierId", default=None, type=int)
    if role in ("community_leader", "supplier"):
        return session.get("user_id")
    return None


def _execute(
    permission_checker: Callable[[], bool],
    action: Callable[[], Dict[str, Any]],
    error_message: str,
) -> Any:
    """统一权限保护执行"""
    try:
        if not permission_checker():
            return jsonify({"code": 403, "message": "权限不足", "data": None})
        return jsonify(action())
    except Exception as exc:
        logger.error("%s: %s", error_message, exc)
        return jsonify({"code": 500, "message": str(exc), "data": None})


@smart_selection_bp.route("/dashboard", methods=["GET"])
@login_required
def get_dashboard():
    return _execute(
        _has_community_permission,
        lambda: service.get_dashboard(_resolve_supplier_id()),
        "获取选品看板失败",
    )


@smart_selection_bp.route("/new-products", methods=["GET"])
@login_required
def get_new_products():
    """商品推荐列表（基于销量预测数据排序）"""
    return _execute(
        _has_community_permission,
        lambda: service.get_new_products(
            _resolve_supplier_id(),
            request.args.get("limit", 50, type=int),
        ),
        "获取商品推荐失败",
    )


@smart_selection_bp.route("/slow-moving", methods=["GET"])
@login_required
def get_slow_moving():
    return _execute(
        _has_community_permission,
        lambda: service.get_slow_moving(
            _resolve_supplier_id(),
            request.args.get("days", 90, type=int),
        ),
        "获取滞销预警失败",
    )


@smart_selection_bp.route("/restock-priority", methods=["GET"])
@login_required
def get_restock_priority():
    return _execute(
        _has_community_permission,
        lambda: service.get_restock_priority(
            _resolve_supplier_id(),
            request.args.get("forecastDays", 7, type=int),
        ),
        "获取补货优先级失败",
    )


@smart_selection_bp.route("/batch-purchase", methods=["POST"])
@login_required
def batch_purchase():
    def action():
        supplier_id = _resolve_supplier_id()
        if not supplier_id:
            return error("无法识别当前用户")
        data = request.get_json(silent=True) or {}
        # 支持新版格式 products=[{productId, quantity}] 和旧版格式 productIds=[1,2,3]
        products = data.get("products")
        if products is None:
            products = [
                {"productId": pid, "quantity": 10}
                for pid in data.get("productIds", [])
            ]
        return service.batch_purchase(supplier_id, products)

    return _execute(
        _has_community_permission,
        action,
        "批量采购失败",
    )


@smart_selection_bp.route("/seasonal", methods=["GET"])
@login_required
def get_seasonal():
    return _execute(
        _has_community_permission,
        lambda: service.get_seasonal(
            _resolve_supplier_id(),
            request.args.get("limit", 20, type=int),
        ),
        "获取季节性选品失败",
    )


@smart_selection_bp.route("/slow-moving/discount", methods=["POST"])
@login_required
def set_slow_moving_discount():
    def action():
        supplier_id = _resolve_supplier_id()
        if not supplier_id:
            return error("无法识别当前用户")
        data = request.get_json(silent=True) or {}
        product_id = data.get("productId")
        discount_rate = data.get("discountRate")
        if not product_id or discount_rate is None:
            return error("缺少参数: productId, discountRate")
        return service.set_slow_moving_discount(supplier_id, product_id, float(discount_rate))

    return _execute(
        _has_community_permission,
        action,
        "设置滞销折扣失败",
    )


@smart_selection_bp.route("/slow-moving/discount", methods=["DELETE"])
@login_required
def clear_slow_moving_discount():
    def action():
        supplier_id = _resolve_supplier_id()
        if not supplier_id:
            return error("无法识别当前用户")
        product_id = request.args.get("productId", type=int)
        if not product_id:
            return error("缺少参数: productId")
        return service.clear_slow_moving_discount(supplier_id, product_id)

    return _execute(
        _has_community_permission,
        action,
        "清除滞销折扣失败",
    )
