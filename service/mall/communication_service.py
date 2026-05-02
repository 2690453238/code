"""
客户沟通服务
"""
from utils.db_utils import get_db_connection
from utils.response import success, error, page_response
from datetime import datetime


class CommunicationService:
    """客户沟通服务类"""
    
    def get_communication_list(self, page=1, limit=10, keyword='', status='', communication_type='', user_id=''):
        """获取客户沟通记录列表（管理员）"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 构建查询条件
                    where_conditions = []
                    params = []
                    
                    if keyword:
                        where_conditions.append("(c.communicationTitle LIKE %s OR c.communicationContent LIKE %s OR u.username LIKE %s)")
                        params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])
                    
                    if status:
                        where_conditions.append("c.status = %s")
                        params.append(status)
                    
                    if communication_type:
                        where_conditions.append("c.communicationType = %s")
                        params.append(communication_type)
                    
                    if user_id:
                        where_conditions.append("c.userId = %s")
                        params.append(user_id)
                    
                    where_clause = ""
                    if where_conditions:
                        where_clause = "WHERE " + " AND ".join(where_conditions)
                    
                    # 查询总数
                    count_sql = f"""
                        SELECT COUNT(*) as total 
                        FROM py_customer_communication c
                        LEFT JOIN py_user u ON c.userId = u.id
                        LEFT JOIN py_user s ON c.salesId = s.id
                        {where_clause}
                    """
                    print(f"执行SQL: {count_sql}, 参数: {params}")
                    cursor.execute(count_sql, params)
                    total = cursor.fetchone()['total']
                    
                    # 查询列表
                    offset = (page - 1) * limit
                    sql = f"""
                        SELECT c.id, c.userId, c.salesId, c.communicationType, 
                               c.communicationTitle, c.communicationContent, c.communicationPurpose,
                               c.customerFeedback, c.nextFollowUpTime, c.status, c.isImportant,
                               c.attachments, c.createTime, c.updateTime,
                               u.username as customerName, u.phone as customerPhone,
                               s.username as salesName
                        FROM py_customer_communication c
                        LEFT JOIN py_user u ON c.userId = u.id
                        LEFT JOIN py_user s ON c.salesId = s.id
                        {where_clause}
                        ORDER BY c.isImportant DESC, c.createTime DESC
                        LIMIT %s OFFSET %s
                    """
                    params.extend([limit, offset])
                    print(f"执行SQL: {sql}, 参数: {params}")
                    cursor.execute(sql, params)
                    rows = cursor.fetchall()
                    
                    # 格式化数据
                    formatted_rows = []
                    for row in rows:
                        formatted_row = {
                            'id': row['id'],
                            'userId': row['userId'],
                            'salesId': row['salesId'],
                            'communicationType': row['communicationType'],
                            'communicationTitle': row['communicationTitle'],
                            'communicationContent': row['communicationContent'],
                            'communicationPurpose': row['communicationPurpose'],
                            'customerFeedback': row['customerFeedback'],
                            'nextFollowUpTime': row['nextFollowUpTime'].strftime('%Y-%m-%d %H:%M:%S') if row['nextFollowUpTime'] else None,
                            'status': row['status'],
                            'isImportant': row['isImportant'],
                            'attachments': row['attachments'],
                            'createTime': row['createTime'].strftime('%Y-%m-%d %H:%M:%S') if row['createTime'] else '',
                            'updateTime': row['updateTime'].strftime('%Y-%m-%d %H:%M:%S') if row['updateTime'] else '',
                            'customerName': row['customerName'],
                            'customerPhone': row['customerPhone'],
                            'salesName': row['salesName']
                        }
                        formatted_rows.append(formatted_row)
                    
                    return page_response(formatted_rows, total, page, limit)
        except Exception as e:
            print(f"获取客户沟通记录列表失败: {e}")
            return error(f"获取客户沟通记录列表失败: {str(e)}")
    
    def get_communication_by_id(self, communication_id):
        """获取客户沟通记录详情"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                        SELECT c.id, c.userId, c.salesId, c.communicationType, 
                               c.communicationTitle, c.communicationContent, c.communicationPurpose,
                               c.customerFeedback, c.nextFollowUpTime, c.status, c.isImportant,
                               c.attachments, c.createTime, c.updateTime,
                               u.username as customerName, u.phone as customerPhone, u.email as customerEmail,
                               s.username as salesName
                        FROM py_customer_communication c
                        LEFT JOIN py_user u ON c.userId = u.id
                        LEFT JOIN py_user s ON c.salesId = s.id
                        WHERE c.id = %s
                    """
                    print(f"执行SQL: {sql}, 参数: {communication_id}")
                    cursor.execute(sql, (communication_id,))
                    row = cursor.fetchone()
                    
                    if not row:
                        return error('沟通记录不存在')
                    
                    data = {
                        'id': row['id'],
                        'userId': row['userId'],
                        'salesId': row['salesId'],
                        'communicationType': row['communicationType'],
                        'communicationTitle': row['communicationTitle'],
                        'communicationContent': row['communicationContent'],
                        'communicationPurpose': row['communicationPurpose'],
                        'customerFeedback': row['customerFeedback'],
                        'nextFollowUpTime': row['nextFollowUpTime'].strftime('%Y-%m-%d %H:%M:%S') if row['nextFollowUpTime'] else None,
                        'status': row['status'],
                        'isImportant': row['isImportant'],
                        'attachments': row['attachments'],
                        'createTime': row['createTime'].strftime('%Y-%m-%d %H:%M:%S') if row['createTime'] else '',
                        'updateTime': row['updateTime'].strftime('%Y-%m-%d %H:%M:%S') if row['updateTime'] else '',
                        'customerName': row['customerName'],
                        'customerPhone': row['customerPhone'],
                        'customerEmail': row['customerEmail'],
                        'salesName': row['salesName']
                    }
                    
                    return success(data)
        except Exception as e:
            print(f"获取客户沟通记录详情失败: {e}")
            return error(f"获取客户沟通记录详情失败: {str(e)}")
    
    def create_communication(self, data, sales_id):
        """创建客户沟通记录"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                        INSERT INTO py_customer_communication 
                        (userId, salesId, communicationType, communicationTitle, communicationContent,
                         communicationPurpose, customerFeedback, nextFollowUpTime, status, isImportant, attachments)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    params = (
                        data.get('userId'),
                        sales_id,
                        data.get('communicationType'),
                        data.get('communicationTitle'),
                        data.get('communicationContent'),
                        data.get('communicationPurpose'),
                        data.get('customerFeedback'),
                        data.get('nextFollowUpTime'),
                        data.get('status', 'pending'),
                        data.get('isImportant', 0),
                        data.get('attachments')
                    )
                    print(f"执行SQL: {sql}, 参数: {params}")
                    cursor.execute(sql, params)
                    conn.commit()
                    
                    return success(None, '创建成功')
        except Exception as e:
            print(f"创建客户沟通记录失败: {e}")
            return error(f"创建客户沟通记录失败: {str(e)}")
    
    def update_communication(self, communication_id, data):
        """更新客户沟通记录"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查记录是否存在
                    check_sql = "SELECT id FROM py_customer_communication WHERE id = %s"
                    cursor.execute(check_sql, (communication_id,))
                    if not cursor.fetchone():
                        return error('沟通记录不存在')
                    
                    sql = """
                        UPDATE py_customer_communication 
                        SET userId = %s, communicationType = %s, communicationTitle = %s,
                            communicationContent = %s, communicationPurpose = %s, customerFeedback = %s,
                            nextFollowUpTime = %s, status = %s, isImportant = %s, attachments = %s
                        WHERE id = %s
                    """
                    params = (
                        data.get('userId'),
                        data.get('communicationType'),
                        data.get('communicationTitle'),
                        data.get('communicationContent'),
                        data.get('communicationPurpose'),
                        data.get('customerFeedback'),
                        data.get('nextFollowUpTime'),
                        data.get('status'),
                        data.get('isImportant', 0),
                        data.get('attachments'),
                        communication_id
                    )
                    print(f"执行SQL: {sql}, 参数: {params}")
                    cursor.execute(sql, params)
                    conn.commit()
                    
                    return success(None, '更新成功')
        except Exception as e:
            print(f"更新客户沟通记录失败: {e}")
            return error(f"更新客户沟通记录失败: {str(e)}")
    
    def delete_communication(self, communication_id):
        """删除客户沟通记录"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查记录是否存在
                    check_sql = "SELECT id FROM py_customer_communication WHERE id = %s"
                    cursor.execute(check_sql, (communication_id,))
                    if not cursor.fetchone():
                        return error('沟通记录不存在')
                    
                    sql = "DELETE FROM py_customer_communication WHERE id = %s"
                    print(f"执行SQL: {sql}, 参数: {communication_id}")
                    cursor.execute(sql, (communication_id,))
                    conn.commit()
                    
                    return success(None, '删除成功')
        except Exception as e:
            print(f"删除客户沟通记录失败: {e}")
            return error(f"删除客户沟通记录失败: {str(e)}")
    
    def update_status(self, communication_id, status):
        """更新沟通记录状态"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    sql = "UPDATE py_customer_communication SET status = %s WHERE id = %s"
                    print(f"执行SQL: {sql}, 参数: {status}, {communication_id}")
                    cursor.execute(sql, (status, communication_id))
                    conn.commit()
                    
                    return success(None, '状态更新成功')
        except Exception as e:
            print(f"更新状态失败: {e}")
            return error(f"更新状态失败: {str(e)}")
    
    def get_customer_list(self):
        """获取客户列表（用于下拉选择）"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                        SELECT id, username, phone, email 
                        FROM py_user 
                        WHERE role = 'user'
                        ORDER BY username
                    """
                    print(f"执行SQL: {sql}")
                    cursor.execute(sql)
                    rows = cursor.fetchall()
                    
                    customers = []
                    for row in rows:
                        customers.append({
                            'id': row['id'],
                            'username': row['username'],
                            'phone': row['phone'],
                            'email': row['email']
                        })
                    
                    return success(customers)
        except Exception as e:
            print(f"获取客户列表失败: {e}")
            return error(f"获取客户列表失败: {str(e)}")
    
    def get_customer_purchase_history(self, user_id):
        """获取客户购买历史（用于个性化推荐）"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                        SELECT o.id, o.orderNo, o.payAmount, o.createTime,
                               oi.productName, oi.quantity, oi.price
                        FROM py_order o
                        LEFT JOIN py_order_item oi ON o.id = oi.orderId
                        WHERE o.userId = %s AND o.status IN ('paid', 'shipped', 'completed')
                        ORDER BY o.createTime DESC
                        LIMIT 10
                    """
                    print(f"执行SQL: {sql}, 参数: {user_id}")
                    cursor.execute(sql, (user_id,))
                    rows = cursor.fetchall()
                    
                    history = []
                    for row in rows:
                        history.append({
                            'orderId': row['id'],
                            'orderNo': row['orderNo'],
                            'payAmount': float(row['payAmount']),
                            'createTime': row['createTime'].strftime('%Y-%m-%d %H:%M:%S') if row['createTime'] else '',
                            'productName': row['productName'],
                            'quantity': row['quantity'],
                            'price': float(row['price'])
                        })
                    
                    return success(history)
        except Exception as e:
            print(f"获取客户购买历史失败: {e}")
            return error(f"获取客户购买历史失败: {str(e)}")

