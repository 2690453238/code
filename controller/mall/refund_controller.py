"""退款退货控制器"""
from flask import Blueprint, request, jsonify, session
from service.mall.refund_service import RefundService
from utils.response import error

refund_bp = Blueprint('mall_refund', __name__, url_prefix='/api/mall/refund')


def _j(result):
    return jsonify(result)


@refund_bp.route('/submit', methods=['POST'])
def submit():
    """用户提交退款申请"""
    if 'user_id' not in session:
        return _j(error('请先登录', 401))
    data = request.get_json() or {}
    order_id = data.get('orderId')
    order_no = data.get('orderNo')
    refund_type = data.get('type', 'only_refund')
    reason = (data.get('reason') or '').strip()
    amount = data.get('amount')
    description = (data.get('description') or '').strip()

    if not order_id or not order_no:
        return _j(error('订单信息不能为空'))
    if refund_type not in ('only_refund', 'return_refund'):
        return _j(error('无效的退款类型'))
    if not reason:
        return _j(error('请填写退款原因'))
    if not amount or float(amount) <= 0:
        return _j(error('退款金额不正确'))

    return _j(RefundService.submit(
        user_id=session['user_id'],
        order_id=order_id,
        order_no=order_no,
        refund_type=refund_type,
        reason=reason,
        amount=amount,
        description=description
    ))


@refund_bp.route('/my-list', methods=['GET'])
def my_list():
    """用户查看自己的退款申请列表"""
    if 'user_id' not in session:
        return _j(error('请先登录', 401))
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    status = request.args.get('status', '').strip()
    return _j(RefundService.my_list(session['user_id'], page, limit, status))


@refund_bp.route('/cancel', methods=['POST'])
def cancel():
    """用户撤销退款申请"""
    if 'user_id' not in session:
        return _j(error('请先登录', 401))
    data = request.get_json() or {}
    refund_id = data.get('id')
    if not refund_id:
        return _j(error('缺少退款ID'))
    return _j(RefundService.cancel(session['user_id'], int(refund_id)))


@refund_bp.route('/admin/list', methods=['GET'])
def admin_list():
    """后台退款申请列表"""
    if 'user_id' not in session:
        return _j(error('请先登录', 401))
    role = session.get('role')
    if role not in ('system_admin', 'platform_operator', 'community_leader'):
        return _j(error('无权限访问'))
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    status = request.args.get('status', '').strip()
    keyword = request.args.get('keyword', '').strip()
    return _j(RefundService.admin_list(page, limit, status, keyword))


@refund_bp.route('/admin/approve', methods=['POST'])
def admin_approve():
    """后台审核退款申请"""
    if 'user_id' not in session:
        return _j(error('请先登录', 401))
    role = session.get('role')
    if role not in ('system_admin', 'platform_operator', 'community_leader'):
        return _j(error('无权限访问'))
    data = request.get_json() or {}
    refund_id = data.get('id')
    approve = data.get('approve', True)
    reply = (data.get('reply', '')).strip()
    if not refund_id:
        return _j(error('缺少退款ID'))
    return _j(RefundService.admin_approve(int(refund_id), session['user_id'], approve, reply))
