"""
投诉反馈控制器 + 蓝图
"""
from flask import Blueprint, request, session, jsonify
from service.complaint_service import ComplaintService
from utils.response import error

complaint_bp = Blueprint('complaint', __name__)


def _j(result):
    """将 dict 结果包装为 jsonify Response"""
    return jsonify(result)


# ----------------------------------------------------------------
# 前台接口
# ----------------------------------------------------------------

@complaint_bp.route('/submit', methods=['POST'])
def front_submit():
    """前台用户提交投诉"""
    if 'user_id' not in session:
        return _j(error('请先登录', 401))
    data = request.get_json() or {}
    complaint_type = data.get('type', 'platform').strip()
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    if not title:
        return _j(error('投诉标题不能为空'))
    if not content:
        return _j(error('投诉内容不能为空'))
    if complaint_type not in ('order', 'product', 'service', 'platform', 'other'):
        return _j(error('无效的投诉类型'))
    import json
    images_raw = data.get('images')
    images = json.dumps(images_raw) if isinstance(images_raw, list) else None
    return _j(ComplaintService.submit(
        user_id=session['user_id'],
        complaint_type=complaint_type,
        title=title,
        content=content,
        images=images,
        order_id=data.get('orderId'),
        order_no=(data.get('orderNo') or '').strip() or None,
        product_id=data.get('productId')
    ))


@complaint_bp.route('/my-list', methods=['GET'])
def front_my_list():
    """前台：我的投诉列表"""
    if 'user_id' not in session:
        return _j(error('请先登录', 401))
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    status = request.args.get('status', '').strip()
    return _j(ComplaintService.my_list(session['user_id'], page, limit, status))


@complaint_bp.route('/rate', methods=['POST'])
def front_rate():
    """前台：评价已解决的投诉"""
    if 'user_id' not in session:
        return _j(error('请先登录', 401))
    data = request.get_json() or {}
    complaint_id = data.get('id')
    rating = data.get('rating')
    if not complaint_id or not rating:
        return _j(error('缺少必要参数'))
    try:
        rating = int(rating)
        if rating not in range(1, 6):
            return _j(error('评分必须在1-5之间'))
    except (ValueError, TypeError):
        return _j(error('评分格式错误'))
    return _j(ComplaintService.rate(
        session['user_id'], int(complaint_id), rating,
        data.get('ratingComment', '').strip()
    ))


@complaint_bp.route('/close', methods=['POST'])
def front_close():
    """前台：撤销/关闭投诉"""
    if 'user_id' not in session:
        return _j(error('请先登录', 401))
    data = request.get_json() or {}
    complaint_id = data.get('id')
    if not complaint_id:
        return _j(error('缺少投诉ID'))
    return _j(ComplaintService.close(session['user_id'], int(complaint_id)))


@complaint_bp.route('/delete', methods=['DELETE'])
def front_delete():
    """前台：删除自己的投诉记录（仅限已关闭/已驳回状态）"""
    if 'user_id' not in session:
        return _j(error('请先登录', 401))
    complaint_id = request.args.get('id')
    if not complaint_id:
        return _j(error('缺少投诉ID'))
    return _j(ComplaintService.user_delete(session['user_id'], int(complaint_id)))


# ----------------------------------------------------------------
# 后台管理接口
# ----------------------------------------------------------------

@complaint_bp.route('/admin/list', methods=['GET'])
def admin_list():
    """后台：投诉列表（分页+筛选）"""
    if 'user_id' not in session:
        return _j(error('请先登录', 401))
    page = int(request.args.get('pageNum', 1))
    limit = int(request.args.get('pageSize', 10))
    status = request.args.get('status', '').strip()
    complaint_type = request.args.get('type', '').strip()
    keyword = request.args.get('keyword', '').strip()
    return _j(ComplaintService.admin_list(page, limit, status, complaint_type, keyword))


@complaint_bp.route('/admin/detail', methods=['GET'])
def admin_detail():
    """后台：投诉详情"""
    if 'user_id' not in session:
        return _j(error('请先登录', 401))
    complaint_id = request.args.get('id')
    if not complaint_id:
        return _j(error('缺少投诉ID'))
    return _j(ComplaintService.admin_detail(int(complaint_id)))


@complaint_bp.route('/admin/reply', methods=['POST'])
def admin_reply():
    """后台：回复投诉并更新状态"""
    if 'user_id' not in session:
        return _j(error('请先登录', 401))
    data = request.get_json() or {}
    complaint_id = data.get('id')
    reply_content = data.get('replyContent', '').strip()
    new_status = data.get('status', 'processing').strip()
    if not complaint_id:
        return _j(error('缺少投诉ID'))
    if not reply_content:
        return _j(error('回复内容不能为空'))
    return _j(ComplaintService.admin_reply(
        int(complaint_id), session['user_id'], reply_content, new_status
    ))


@complaint_bp.route('/admin/update-status', methods=['POST'])
def admin_update_status():
    """后台：仅更新投诉状态"""
    if 'user_id' not in session:
        return _j(error('请先登录', 401))
    data = request.get_json() or {}
    complaint_id = data.get('id')
    new_status = data.get('status', '').strip()
    if not complaint_id or not new_status:
        return _j(error('缺少必要参数'))
    return _j(ComplaintService.admin_update_status(int(complaint_id), new_status))


@complaint_bp.route('/admin/delete', methods=['DELETE'])
def admin_delete():
    """后台：删除投诉记录"""
    if 'user_id' not in session:
        return _j(error('请先登录', 401))
    complaint_id = request.args.get('id')
    if not complaint_id:
        return _j(error('缺少投诉ID'))
    return _j(ComplaintService.admin_delete(int(complaint_id)))

