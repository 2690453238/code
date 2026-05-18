"""退款退货服务"""
import random
import string
from datetime import datetime
from decimal import Decimal
from utils.db_utils import get_db_connection
from utils.response import success, error, page_response


def _gen_refund_no():
    now = datetime.now().strftime('%Y%m%d%H%M%S')
    suffix = ''.join(random.choices(string.digits, k=4))
    return f'RF{now}{suffix}'


class RefundService:

    @staticmethod
    def submit(user_id, order_id, order_no, refund_type, reason, amount, description='', images=None):
        """用户提交退款申请"""
        try:
            # 验证订单
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, status, payAmount, supplierId FROM py_order WHERE id=%s AND userId=%s",
                        (order_id, user_id)
                    )
                    order = cur.fetchone()
                    if not order:
                        return error('订单不存在')
                    if order['status'] in ('pending', 'cancelled', 'cancel_requested'):
                        return error('当前订单状态不可申请退款')

                    # 检查是否有进行中的退款申请
                    cur.execute(
                        "SELECT id FROM py_refund WHERE orderId=%s AND userId=%s AND status='pending'",
                        (order_id, user_id)
                    )
                    if cur.fetchone():
                        return error('该订单已有进行中的退款申请')

                    # 检查退款金额
                    if amount is None or float(amount) <= 0:
                        return error('退款金额不正确')
                    if float(amount) > float(order['payAmount']):
                        return error('退款金额不能超过实付金额')

                    refund_no = _gen_refund_no()
                    now_dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    sql = """INSERT INTO py_refund (orderId, orderNo, userId, supplierId, refundNo,
                        type, reason, amount, description, images, status, createTime, updateTime)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending',%s,%s)"""
                    cur.execute(sql, (
                        order_id, order_no, user_id, order['supplierId'], refund_no,
                        refund_type, reason, amount, description, images, now_dt, now_dt
                    ))
                    conn.commit()
                    return success({'refundNo': refund_no}, '退款申请已提交，请等待审核')
        except Exception as e:
            print(f'提交退款申请失败: {e}')
            return error(f'提交失败: {str(e)}')

    @staticmethod
    def my_list(user_id, page=1, limit=10, status=''):
        """获取当前用户的退款申请列表"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    where = ['userId = %s']
                    params = [user_id]
                    if status:
                        where.append('status = %s')
                        params.append(status)
                    where_sql = 'WHERE ' + ' AND '.join(where)

                    cur.execute(f'SELECT COUNT(*) AS total FROM py_refund {where_sql}', params)
                    total = cur.fetchone()['total']

                    offset = (page - 1) * limit
                    cur.execute(
                        f"""SELECT id, orderId, orderNo, refundNo, type, reason, amount,
                            description, images, status, adminReply, createTime, updateTime
                        FROM py_refund {where_sql}
                        ORDER BY createTime DESC LIMIT %s OFFSET %s""",
                        params + [limit, offset]
                    )
                    rows = cur.fetchall()
                    return page_response(rows, total, page, limit)
        except Exception as e:
            print(f'获取退款列表失败: {e}')
            return error(str(e))

    @staticmethod
    def admin_list(page=1, limit=10, status='', keyword=''):
        """后台获取退款申请列表"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    where = ['1=1']
                    params = []
                    if status:
                        where.append('r.status = %s')
                        params.append(status)
                    if keyword:
                        where.append('(r.refundNo LIKE %s OR r.orderNo LIKE %s OR u.username LIKE %s)')
                        kw = f'%{keyword}%'
                        params.extend([kw, kw, kw])
                    where_sql = 'WHERE ' + ' AND '.join(where)

                    cur.execute(
                        f'SELECT COUNT(*) AS total FROM py_refund r LEFT JOIN py_user u ON r.userId=u.id {where_sql}',
                        params
                    )
                    total = cur.fetchone()['total']

                    offset = (page - 1) * limit
                    cur.execute(
                        f"""SELECT r.id, r.orderId, r.orderNo, r.refundNo, r.type, r.reason,
                            r.amount, r.description, r.status, r.adminReply, r.createTime, r.updateTime,
                            u.username, u.nickname
                        FROM py_refund r LEFT JOIN py_user u ON r.userId=u.id
                        {where_sql}
                        ORDER BY r.createTime DESC LIMIT %s OFFSET %s""",
                        params + [limit, offset]
                    )
                    rows = cur.fetchall()
                    return page_response(rows, total, page, limit)
        except Exception as e:
            print(f'后台获取退款列表失败: {e}')
            return error(str(e))

    @staticmethod
    def admin_approve(refund_id, admin_id, approve=True, reply=''):
        """管理员审核退款申请"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, status, orderId, type FROM py_refund WHERE id=%s", (refund_id,))
                    refund = cur.fetchone()
                    if not refund:
                        return error('退款记录不存在')
                    if refund['status'] != 'pending':
                        return error('该退款申请已处理')

                    new_status = 'approved' if approve else 'rejected'
                    now_dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    cur.execute(
                        "UPDATE py_refund SET status=%s, adminReply=%s, adminId=%s, updateTime=%s WHERE id=%s",
                        (new_status, reply, admin_id, now_dt, refund_id)
                    )

                    # 如果通过，将订单设为已取消
                    if approve and refund['type'] == 'only_refund':
                        cur.execute(
                            "UPDATE py_order SET status='cancelled', updateTime=%s WHERE id=%s",
                            (now_dt, refund['orderId'])
                        )
                    elif approve and refund['type'] == 'return_refund':
                        cur.execute(
                            "UPDATE py_order SET status='cancelled', updateTime=%s WHERE id=%s",
                            (now_dt, refund['orderId'])
                        )

                    conn.commit()
                    msg = '退款申请已通过' if approve else '退款申请已拒绝'
                    return success(None, msg)
        except Exception as e:
            print(f'审核退款申请失败: {e}')
            return error(f'审核失败: {str(e)}')

    @staticmethod
    def cancel(user_id, refund_id):
        """用户撤销退款申请"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, status FROM py_refund WHERE id=%s AND userId=%s",
                        (refund_id, user_id)
                    )
                    refund = cur.fetchone()
                    if not refund:
                        return error('退款记录不存在')
                    if refund['status'] != 'pending':
                        return error('只能撤销待处理的退款申请')
                    cur.execute(
                        "UPDATE py_refund SET status='cancelled', updateTime=NOW() WHERE id=%s",
                        (refund_id,)
                    )
                    conn.commit()
                    return success(None, '退款申请已撤销')
        except Exception as e:
            print(f'撤销退款申请失败: {e}')
            return error(str(e))
