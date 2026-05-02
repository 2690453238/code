"""
投诉反馈服务层
"""
import random
import string
from datetime import datetime
from utils.db_utils import get_db_connection
from utils.response import success, error, page_response


def _gen_complaint_no():
    """生成投诉单号：CP + 年月日时分秒 + 4位随机数"""
    now = datetime.now().strftime('%Y%m%d%H%M%S')
    suffix = ''.join(random.choices(string.digits, k=4))
    return f'CP{now}{suffix}'


class ComplaintService:
    """投诉反馈服务类"""

    # ----------------------------------------------------------------
    # 前台接口
    # ----------------------------------------------------------------

    @staticmethod
    def submit(user_id, complaint_type, title, content, images=None,
               order_id=None, order_no=None, product_id=None):
        """用户提交投诉"""
        try:
            complaint_no = _gen_complaint_no()
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    sql = """
                        INSERT INTO py_complaint
                            (userId, complaintNo, type, orderId, orderNo, productId,
                             title, content, images, status, priority, createTime, updateTime)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending',1,NOW(),NOW())
                    """
                    cur.execute(sql, (
                        user_id, complaint_no, complaint_type,
                        order_id, order_no, product_id,
                        title, content, images
                    ))
                    conn.commit()
                    return success({'complaintNo': complaint_no}, '投诉提交成功，我们将在3个工作日内处理')
        except Exception as e:
            print(f'提交投诉失败: {e}')
            return error(f'提交失败: {str(e)}')

    @staticmethod
    def my_list(user_id, page=1, limit=10, status=''):
        """获取当前用户投诉列表"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    where = ['userId = %s']
                    params = [user_id]
                    if status:
                        where.append('status = %s')
                        params.append(status)
                    where_sql = 'WHERE ' + ' AND '.join(where)

                    cur.execute(f'SELECT COUNT(*) AS total FROM py_complaint {where_sql}', params)
                    total = cur.fetchone()['total']

                    # 待处理数量
                    cur.execute(
                        "SELECT COUNT(*) AS cnt FROM py_complaint WHERE userId=%s AND status='pending'",
                        [user_id]
                    )
                    pending_count = cur.fetchone()['cnt']

                    offset = (page - 1) * limit
                    cur.execute(
                        f"""
                        SELECT id, complaintNo, type, orderId, orderNo, title, content, images,
                               status, priority, replyContent, replyTime,
                               rating, ratingComment, createTime, updateTime
                        FROM py_complaint {where_sql}
                        ORDER BY createTime DESC
                        LIMIT %s OFFSET %s
                        """,
                        params + [limit, offset]
                    )
                    rows = cur.fetchall()
                    result = page_response(rows, total, page, limit)
                    result['data']['pendingCount'] = pending_count
                    return result
        except Exception as e:
            print(f'获取我的投诉列表失败: {e}')
            return error(str(e))

    @staticmethod
    def rate(user_id, complaint_id, rating, rating_comment=''):
        """用户对已解决投诉进行评价"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, status, rating FROM py_complaint WHERE id=%s AND userId=%s",
                        [complaint_id, user_id]
                    )
                    row = cur.fetchone()
                    if not row:
                        return error('投诉记录不存在')
                    if row['status'] != 'resolved':
                        return error('只能对已解决的投诉进行评价')
                    if row['rating']:
                        return error('已评价，不能重复提交')
                    cur.execute(
                        """
                        UPDATE py_complaint
                        SET rating=%s, ratingComment=%s, ratingTime=NOW(), updateTime=NOW()
                        WHERE id=%s
                        """,
                        [rating, rating_comment, complaint_id]
                    )
                    conn.commit()
                    return success(None, '评价成功')
        except Exception as e:
            print(f'评价失败: {e}')
            return error(str(e))

    @staticmethod
    def close(user_id, complaint_id):
        """用户撤销/关闭投诉（仅限 pending 状态）"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, status FROM py_complaint WHERE id=%s AND userId=%s",
                        [complaint_id, user_id]
                    )
                    row = cur.fetchone()
                    if not row:
                        return error('投诉记录不存在')
                    if row['status'] != 'pending':
                        return error('只有待处理的投诉才能撤销')
                    cur.execute(
                        "UPDATE py_complaint SET status='closed', updateTime=NOW() WHERE id=%s",
                        [complaint_id]
                    )
                    conn.commit()
                    return success(None, '投诉已撤销')
        except Exception as e:
            print(f'撤销投诉失败: {e}')
            return error(str(e))

    @staticmethod
    def user_delete(user_id, complaint_id):
        """用户删除自己的投诉记录（仅限已关闭/已驳回状态）"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, status FROM py_complaint WHERE id=%s AND userId=%s",
                        [complaint_id, user_id]
                    )
                    row = cur.fetchone()
                    if not row:
                        return error('投诉记录不存在')
                    if row['status'] not in ('closed', 'rejected', 'resolved'):
                        return error('只能删除已关闭、已驳回或已解决的投诉记录')
                    cur.execute('DELETE FROM py_complaint WHERE id=%s', [complaint_id])
                    conn.commit()
                    return success(None, '删除成功')
        except Exception as e:
            print(f'用户删除投诉失败: {e}')
            return error(str(e))

    # ----------------------------------------------------------------
    # 后台管理接口
    # ----------------------------------------------------------------

    @staticmethod
    def admin_list(page=1, limit=10, status='', complaint_type='', keyword=''):
        """后台获取投诉列表（分页+筛选，不包含已关闭的投诉）"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    where = ["c.status != 'closed'"]
                    params = []
                    if status:
                        where.append('c.status = %s')
                        params.append(status)
                    if complaint_type:
                        where.append('c.type = %s')
                        params.append(complaint_type)
                    if keyword:
                        where.append('(c.title LIKE %s OR c.complaintNo LIKE %s OR u.username LIKE %s)')
                        kw = f'%{keyword}%'
                        params.extend([kw, kw, kw])
                    where_sql = 'WHERE ' + ' AND '.join(where)

                    cur.execute(
                        f'SELECT COUNT(*) AS total FROM py_complaint c '
                        f'LEFT JOIN py_user u ON c.userId=u.id {where_sql}',
                        params
                    )
                    total = cur.fetchone()['total']

                    # 各状态统计（不含已关闭）
                    cur.execute("""
                        SELECT status, COUNT(*) AS cnt FROM py_complaint
                        WHERE status != 'closed' GROUP BY status
                    """)
                    status_stats = {r['status']: r['cnt'] for r in cur.fetchall()}

                    offset = (page - 1) * limit
                    cur.execute(
                        f"""
                        SELECT c.id, c.complaintNo, c.type, c.orderId, c.orderNo,
                               c.title, c.content, c.images, c.status, c.priority,
                               c.replyContent, c.replyUserId, c.replyTime,
                               c.rating, c.ratingComment, c.resolvedTime,
                               c.createTime, c.updateTime,
                               u.username, u.nickname, u.phone
                        FROM py_complaint c
                        LEFT JOIN py_user u ON c.userId = u.id
                        {where_sql}
                        ORDER BY
                            FIELD(c.status,'pending','processing','resolved','rejected'),
                            c.priority DESC, c.createTime DESC
                        LIMIT %s OFFSET %s
                        """,
                        params + [limit, offset]
                    )
                    rows = cur.fetchall()
                    result = page_response(rows, total, page, limit)
                    result['data']['statusStats'] = status_stats
                    return result
        except Exception as e:
            print(f'后台获取投诉列表失败: {e}')
            return error(str(e))

    @staticmethod
    def admin_detail(complaint_id):
        """后台获取投诉详情"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT c.*, u.username, u.nickname, u.phone, u.email
                        FROM py_complaint c
                        LEFT JOIN py_user u ON c.userId = u.id
                        WHERE c.id = %s
                        """,
                        [complaint_id]
                    )
                    row = cur.fetchone()
                    if not row:
                        return error('投诉记录不存在')
                    return success(row)
        except Exception as e:
            print(f'获取投诉详情失败: {e}')
            return error(str(e))

    @staticmethod
    def admin_reply(complaint_id, admin_id, reply_content, new_status):
        """后台回复并更新投诉状态"""
        try:
            valid_statuses = ('pending', 'processing', 'resolved', 'rejected')
            if new_status not in valid_statuses:
                return error('无效的状态值')
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT id FROM py_complaint WHERE id=%s', [complaint_id])
                    if not cur.fetchone():
                        return error('投诉记录不存在')
                    resolved_time_sql = ', resolvedTime=NOW()' if new_status == 'resolved' else ''
                    cur.execute(
                        f"""
                        UPDATE py_complaint
                        SET replyContent=%s, replyUserId=%s, replyTime=NOW(),
                            status=%s {resolved_time_sql}, updateTime=NOW()
                        WHERE id=%s
                        """,
                        [reply_content, admin_id, new_status, complaint_id]
                    )
                    conn.commit()
                    return success(None, '回复成功')
        except Exception as e:
            print(f'回复投诉失败: {e}')
            return error(str(e))

    @staticmethod
    def admin_update_status(complaint_id, new_status):
        """后台单独更新投诉状态"""
        try:
            valid_statuses = ('pending', 'processing', 'resolved', 'rejected', 'closed')
            if new_status not in valid_statuses:
                return error('无效的状态值')
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT id FROM py_complaint WHERE id=%s', [complaint_id])
                    if not cur.fetchone():
                        return error('投诉记录不存在')
                    resolved_sql = ', resolvedTime=NOW()' if new_status == 'resolved' else ''
                    cur.execute(
                        f"UPDATE py_complaint SET status=%s{resolved_sql}, updateTime=NOW() WHERE id=%s",
                        [new_status, complaint_id]
                    )
                    conn.commit()
                    return success(None, '状态更新成功')
        except Exception as e:
            print(f'更新投诉状态失败: {e}')
            return error(str(e))

    @staticmethod
    def admin_delete(complaint_id):
        """后台删除已关闭/已解决的投诉记录"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, status FROM py_complaint WHERE id=%s", [complaint_id]
                    )
                    row = cur.fetchone()
                    if not row:
                        return error('投诉记录不存在')
                    cur.execute('DELETE FROM py_complaint WHERE id=%s', [complaint_id])
                    conn.commit()
                    return success(None, '删除成功')
        except Exception as e:
            print(f'删除投诉失败: {e}')
            return error(str(e))

