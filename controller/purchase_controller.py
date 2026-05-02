"""采购订单管理控制器"""
from flask import Blueprint, jsonify, request, session

from service.purchase_service import PurchaseService
from utils.auth_utils import login_required
from utils.response import error

purchase_bp = Blueprint("purchase", __name__, url_prefix="/api/supplier/purchase")
service = PurchaseService()


def _resolve_supplier_id():
    role = session.get("role")
    if role in ("community_leader", "supplier"):
        return session.get("user_id")
    return None


@purchase_bp.route("/orders", methods=["GET"])
@login_required
def get_orders():
    supplier_id = _resolve_supplier_id()
    if not supplier_id:
        return jsonify(error("无权访问"))
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)
    status = request.args.get("status", type=str)
    return jsonify(service.get_orders(supplier_id, page, limit, status))


@purchase_bp.route("/orders/<int:order_id>", methods=["GET"])
@login_required
def get_order_detail(order_id):
    supplier_id = _resolve_supplier_id()
    if not supplier_id:
        return jsonify(error("无权访问"))
    return jsonify(service.get_order_detail(order_id, supplier_id))


@purchase_bp.route("/orders/<int:order_id>", methods=["PUT"])
@login_required
def update_order(order_id):
    supplier_id = _resolve_supplier_id()
    if not supplier_id:
        return jsonify(error("无权访问"))
    data = request.get_json(silent=True) or {}
    items = data.get("items", [])
    return jsonify(service.update_order(order_id, supplier_id, items))


@purchase_bp.route("/orders/<int:order_id>/confirm", methods=["POST"])
@login_required
def confirm_order(order_id):
    supplier_id = _resolve_supplier_id()
    if not supplier_id:
        return jsonify(error("无权访问"))
    return jsonify(service.confirm_order(order_id, supplier_id))


@purchase_bp.route("/orders/<int:order_id>/pay", methods=["POST"])
@login_required
def pay_order(order_id):
    supplier_id = _resolve_supplier_id()
    if not supplier_id:
        return jsonify(error("无权访问"))
    return jsonify(service.pay_order(order_id, supplier_id))


@purchase_bp.route("/orders/<int:order_id>/cancel", methods=["POST"])
@login_required
def cancel_order(order_id):
    supplier_id = _resolve_supplier_id()
    if not supplier_id:
        return jsonify(error("无权访问"))
    return jsonify(service.cancel_order(order_id, supplier_id))
