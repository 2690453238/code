"""
订单数据模型
"""
from typing import List, Dict, Optional
from datetime import datetime
import uuid


class OrderModel:
    """订单模型"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def create_order(self, user_id: int, order_data: Dict) -> int:
        """创建订单"""
        with self.db.cursor() as cursor:
            # 生成订单号
            order_no = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"
            
            sql = """
                INSERT INTO py_order (orderNo, userId, status, totalAmount, payAmount, 
                                    discountAmount, couponId, remark)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                order_no,
                user_id,
                order_data.get('status', 1),
                order_data['totalAmount'],
                order_data['payAmount'],
                order_data.get('discountAmount', 0),
                order_data.get('couponId'),
                order_data.get('remark', '')
            )
            print(f"执行SQL: {sql}, 参数: {params}")
            cursor.execute(sql, params)
            # 添加事务提交
            self.db.commit()
            print(f"订单创建成功，ID: {cursor.lastrowid}")
            return cursor.lastrowid
    
    def get_orders_by_user(self, user_id: int, page: int = 1, limit: int = 10) -> Dict:
        """获取用户订单列表"""
        with self.db.cursor() as cursor:
            # 查询总数
            count_sql = "SELECT COUNT(*) as total FROM py_order WHERE userId = %s"
            print(f"执行SQL: {count_sql}, 参数: {user_id}")
            cursor.execute(count_sql, (user_id,))
            total = cursor.fetchone()['total']
            
            # 查询数据
            offset = (page - 1) * limit
            data_sql = """
                SELECT id, orderNo, userId, status, totalAmount, payAmount, discountAmount,
                       couponId, payMethod, payTime, shipTime, finishTime, cancelTime,
                       remark, createTime, updateTime
                FROM py_order
                WHERE userId = %s
                ORDER BY createTime DESC
                LIMIT %s OFFSET %s
            """
            print(f"执行SQL: {data_sql}, 参数: {user_id, limit, offset}")
            cursor.execute(data_sql, (user_id, limit, offset))
            rows = cursor.fetchall()
            
            return {
                'total': total,
                'page': page,
                'limit': limit,
                'rows': rows
            }
    
    def get_order_by_id(self, order_id: int) -> Optional[Dict]:
        """根据ID获取订单详情"""
        with self.db.cursor() as cursor:
            sql = """
                SELECT id, orderNo, userId, status, totalAmount, payAmount, discountAmount,
                       couponId, payMethod, payTime, shipTime, finishTime, cancelTime,
                       remark, createTime, updateTime
                FROM py_order
                WHERE id = %s
            """
            print(f"执行SQL: {sql}, 参数: {order_id}")
            cursor.execute(sql, (order_id,))
            return cursor.fetchone()
    
    def get_order_by_no(self, order_no: str) -> Optional[Dict]:
        """根据订单号获取订单"""
        with self.db.cursor() as cursor:
            sql = """
                SELECT id, orderNo, userId, status, totalAmount, payAmount, discountAmount,
                       couponId, payMethod, payTime, shipTime, finishTime, cancelTime,
                       remark, createTime, updateTime
                FROM py_order
                WHERE orderNo = %s
            """
            print(f"执行SQL: {sql}, 参数: {order_no}")
            cursor.execute(sql, (order_no,))
            return cursor.fetchone()
    
    def update_order_status(self, order_id: int, status: int, **kwargs) -> bool:
        """更新订单状态"""
        with self.db.cursor() as cursor:
            update_fields = ["status = %s"]
            params = [status]
            
            # 根据状态设置对应时间
            if status == 2 and 'payTime' in kwargs:  # 已付款
                update_fields.append("payTime = %s")
                params.append(kwargs['payTime'])
            elif status == 3 and 'shipTime' in kwargs:  # 已发货
                update_fields.append("shipTime = %s")
                params.append(kwargs['shipTime'])
            elif status == 4 and 'finishTime' in kwargs:  # 已完成
                update_fields.append("finishTime = %s")
                params.append(kwargs['finishTime'])
            elif status == 5 and 'cancelTime' in kwargs:  # 已取消
                update_fields.append("cancelTime = %s")
                params.append(kwargs['cancelTime'])
            
            if 'payMethod' in kwargs:
                update_fields.append("payMethod = %s")
                params.append(kwargs['payMethod'])
            
            params.append(order_id)
            sql = f"UPDATE py_order SET {', '.join(update_fields)} WHERE id = %s"
            print(f"执行SQL: {sql}, 参数: {params}")
            cursor.execute(sql, params)
            # 添加事务提交
            self.db.commit()
            print(f"订单状态更新成功，影响行数: {cursor.rowcount}")
            return cursor.rowcount > 0
    
    def cancel_order(self, order_id: int) -> bool:
        """取消订单"""
        return self.update_order_status(order_id, 5, cancelTime=datetime.now())
    
    def get_admin_orders(self, page: int = 1, limit: int = 10, order_no: str = '', 
                        username: str = '', status: int = None, 
                        start_time: str = '', end_time: str = '') -> Dict:
        """管理员获取订单列表"""
        with self.db.cursor() as cursor:
            # 构建查询条件
            where_conditions = []
            params = []
            
            if order_no:
                where_conditions.append("o.orderNo LIKE %s")
                params.append(f"%{order_no}%")
            
            if username:
                where_conditions.append("u.username LIKE %s")
                params.append(f"%{username}%")
            
            if status is not None:
                where_conditions.append("o.status = %s")
                params.append(status)
            
            if start_time:
                where_conditions.append("o.createTime >= %s")
                params.append(start_time)
            
            if end_time:
                where_conditions.append("o.createTime <= %s")
                params.append(end_time)
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # 查询总数
            count_sql = f"""
                SELECT COUNT(*) as total 
                FROM py_order o
                LEFT JOIN py_user u ON o.userId = u.id
                WHERE {where_clause}
            """
            print(f"执行SQL: {count_sql}, 参数: {params}")
            cursor.execute(count_sql, params)
            total = cursor.fetchone()['total']
            
            # 查询数据
            offset = (page - 1) * limit
            data_sql = f"""
                SELECT o.id, o.orderNo, o.userId, o.status, o.totalAmount, o.payAmount, 
                       o.discountAmount, o.couponId, o.payMethod, o.payTime, o.shipTime, 
                       o.finishTime, o.cancelTime, o.remark, o.createTime, o.updateTime,
                       u.username, u.nickname
                FROM py_order o
                LEFT JOIN py_user u ON o.userId = u.id
                WHERE {where_clause}
                ORDER BY o.createTime DESC
                LIMIT %s OFFSET %s
            """
            data_params = params + [limit, offset]
            print(f"执行SQL: {data_sql}, 参数: {data_params}")
            cursor.execute(data_sql, data_params)
            rows = cursor.fetchall()
            
            return {
                'total': total,
                'page': page,
                'limit': limit,
                'rows': rows
            }


class OrderItemModel:
    """订单商品模型"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def create_order_items(self, order_id: int, items: List[Dict]) -> bool:
        """创建订单商品"""
        with self.db.cursor() as cursor:
            sql = """
                INSERT INTO py_order_item (orderId, productId, skuId, productName, 
                                         skuName, productImage, price, quantity, totalAmount)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            for item in items:
                params = (
                    order_id,
                    item['productId'],
                    item.get('skuId'),
                    item['productName'],
                    item.get('skuName'),
                    item.get('productImage'),
                    item['price'],
                    item['quantity'],
                    item['totalAmount']
                )
                print(f"执行SQL: {sql}, 参数: {params}")
                cursor.execute(sql, params)
            # 添加事务提交
            self.db.commit()
            print(f"订单商品创建成功，订单ID: {order_id}")
            return True
    
    def get_order_items(self, order_id: int) -> List[Dict]:
        """获取订单商品列表"""
        with self.db.cursor() as cursor:
            sql = """
                SELECT id, orderId, productId, skuId, productName, skuName, 
                       productImage, price, quantity, totalAmount, createTime
                FROM py_order_item
                WHERE orderId = %s
                ORDER BY createTime ASC
            """
            print(f"执行SQL: {sql}, 参数: {order_id}")
            cursor.execute(sql, (order_id,))
            return cursor.fetchall()
