"""仓库管理控制器"""
from flask import Blueprint, jsonify, request, session

from service.warehouse_service import WarehouseService
from utils.auth_utils import login_required
from utils.response import error

warehouse_bp = Blueprint("warehouse", __name__, url_prefix="/api/supplier/warehouse")
service = WarehouseService()


def _resolve_supplier_id():
    role = session.get("role")
    if role in ("community_leader", "supplier"):
        return session.get("user_id")
    return None


@warehouse_bp.route("", methods=["GET"])
@login_required
def get_warehouse_list():
    supplier_id = _resolve_supplier_id()
    if not supplier_id:
        return jsonify(error("无权访问"))
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)
    keyword = request.args.get("keyword", "", type=str)
    return jsonify(service.get_warehouse_list(supplier_id, page, limit, keyword))


@warehouse_bp.route("/stats", methods=["GET"])
@login_required
def get_warehouse_stats():
    supplier_id = _resolve_supplier_id()
    if not supplier_id:
        return jsonify(error("无权访问"))
    return jsonify(service.get_warehouse_stats(supplier_id))
