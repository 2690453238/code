"""
社区团长服务层
实现社区团长相关的业务逻辑和数据隔离
"""
from utils.db_utils import get_db_connection


class SupplierService:
    """社区团长服务类"""

    GLOBAL_ROLES = ['system_admin', 'platform_operator']

    @staticmethod
    def _build_scope(user_info):
        """构建社区范围过滤条件"""
        if user_info['role'] in SupplierService.GLOBAL_ROLES:
            return "", []
        return "WHERE supplierId = %s", [user_info['id']]

    @staticmethod
    def get_supplier_stats(user_info):
        """获取社区团长统计数据"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                supplier_condition, supplier_params = SupplierService._build_scope(user_info)

                product_sql = f"""
                    SELECT
                        COUNT(*) as productCount,
                        COUNT(CASE WHEN status = 1 THEN 1 END) as onlineCount,
                        COUNT(CASE WHEN stock < 10 THEN 1 END) as lowStockCount
                    FROM py_product
                    {supplier_condition} {"AND" if supplier_condition else "WHERE"} status != -1
                """
                cursor.execute(product_sql, supplier_params if supplier_params else None)
                product_stats = cursor.fetchone()

                order_sql = f"""
                    SELECT
                        COUNT(*) as orderCount,
                        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pendingCount,
                        COALESCE(SUM(totalAmount), 0) as totalAmount
                    FROM py_order
                    {supplier_condition}
                """
                cursor.execute(order_sql, supplier_params if supplier_params else None)
                order_stats = cursor.fetchone()

                month_sql = f"""
                    SELECT COALESCE(SUM(totalAmount), 0) as monthAmount
                    FROM py_order
                    {supplier_condition}
                    {"AND" if supplier_condition else "WHERE"} DATE_FORMAT(
                        STR_TO_DATE(createTime, '%%Y-%%m-%%d %%H:%%i:%%s'),
                        '%%Y-%%m'
                    ) = DATE_FORMAT(NOW(), '%%Y-%%m')
                """
                cursor.execute(month_sql, supplier_params if supplier_params else None)
                month_stats = cursor.fetchone()

                return {
                    'productCount': product_stats['productCount'] or 0,
                    'onlineCount': product_stats['onlineCount'] or 0,
                    'lowStockCount': product_stats['lowStockCount'] or 0,
                    'orderCount': order_stats['orderCount'] or 0,
                    'pendingCount': order_stats['pendingCount'] or 0,
                    'totalAmount': float(order_stats['totalAmount'] or 0),
                    'monthAmount': float(month_stats['monthAmount'] or 0)
                }
        finally:
            conn.close()

    @staticmethod
    def get_top_products(user_info, limit=10):
        """获取热销商品 TOP N"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                supplier_condition, params = SupplierService._build_scope(user_info)
                query_params = params + [limit]
                sql = f"""
                    SELECT id, name, price, stock, sales, status
                    FROM py_product
                    {supplier_condition}
                    {"AND" if supplier_condition else "WHERE"} status != -1
                    ORDER BY sales DESC
                    LIMIT %s
                """
                cursor.execute(sql, query_params)
                return cursor.fetchall()
        finally:
            conn.close()

    @staticmethod
    def get_order_trend(user_info, days=30):
        """获取近期订单趋势"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                conditions = ["status IN ('paid', 'shipped', 'delivered', 'completed')"]
                params = []

                if user_info['role'] not in SupplierService.GLOBAL_ROLES:
                    conditions.append("supplierId = %s")
                    params.append(user_info['id'])

                where_clause = " AND ".join(conditions)
                sql = f"""
                    SELECT DATE(STR_TO_DATE(createTime, '%%Y-%%m-%%d %%H:%%i:%%s')) AS order_date,
                           COUNT(*) AS order_count,
                           COALESCE(SUM(payAmount), 0) AS revenue
                    FROM py_order
                    WHERE {where_clause}
                      AND STR_TO_DATE(createTime, '%%Y-%%m-%%d %%H:%%i:%%s') >= DATE_SUB(NOW(), INTERVAL %s DAY)
                    GROUP BY DATE(STR_TO_DATE(createTime, '%%Y-%%m-%%d %%H:%%i:%%s'))
                    ORDER BY order_date
                """
                cursor.execute(sql, params + [days])
                rows = cursor.fetchall()

                if not rows and days < 180:
                    cursor.execute(sql, params + [180])
                    rows = cursor.fetchall()

                return {
                    'dates': [
                        row['order_date'].strftime('%m-%d') if hasattr(row['order_date'], 'strftime') else str(row['order_date'])
                        for row in rows
                    ],
                    'orderCounts': [int(row['order_count'] or 0) for row in rows],
                    'revenues': [float(row['revenue'] or 0) for row in rows]
                }
        finally:
            conn.close()

    @staticmethod
    def get_supplier_products(user_info, page_num=1, page_size=10, keyword='', status=None, category_id=None):
        """获取社区团长的商品列表"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                conditions = ["status != -1"]
                params = []

                if user_info['role'] not in SupplierService.GLOBAL_ROLES:
                    conditions.insert(0, "supplierId = %s")
                    params.append(user_info['id'])

                if keyword:
                    conditions.append("(name LIKE %s OR brand LIKE %s)")
                    params.extend([f'%{keyword}%', f'%{keyword}%'])

                if category_id:
                    conditions.append("categoryId = %s")
                    params.append(category_id)

                if status is not None:
                    conditions.append("status = %s")
                    params.append(status)

                where_clause = " AND ".join(conditions)
                count_sql = f"SELECT COUNT(*) as total FROM py_product WHERE {where_clause}"
                cursor.execute(count_sql, params)
                total = cursor.fetchone()['total']

                offset = (page_num - 1) * page_size
                data_sql = f"""
                    SELECT id, name, price, originalPrice, stock, sales, status,
                           mainImage, categoryId, brand, isHot, isNew, createTime
                    FROM py_product
                    WHERE {where_clause}
                    ORDER BY createTime DESC
                    LIMIT %s OFFSET %s
                """
                data_params = params + [page_size, offset]
                cursor.execute(data_sql, data_params)
                rows = cursor.fetchall()

                return {
                    'total': total,
                    'pageNum': page_num,
                    'pageSize': page_size,
                    'rows': rows
                }
        finally:
            conn.close()

    @staticmethod
    def get_supplier_orders(user_info, page_num=1, page_size=10, status=None):
        """获取社区团长的订单列表"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                conditions = []
                params = []

                if user_info['role'] not in SupplierService.GLOBAL_ROLES:
                    conditions.append("supplierId = %s")
                    params.append(user_info['id'])

                if status:
                    conditions.append("status = %s")
                    params.append(status)

                where_clause = " AND ".join(conditions) if conditions else "1 = 1"
                count_sql = f"SELECT COUNT(*) as total FROM py_order WHERE {where_clause}"
                cursor.execute(count_sql, params)
                total = cursor.fetchone()['total']

                offset = (page_num - 1) * page_size
                data_sql = f"""
                    SELECT id, orderNo, userId, totalAmount, payAmount, status,
                           payStatus, shippingStatus, receiverName, receiverPhone,
                           createTime, updateTime
                    FROM py_order
                    WHERE {where_clause}
                    ORDER BY createTime DESC
                    LIMIT %s OFFSET %s
                """
                data_params = params + [page_size, offset]
                cursor.execute(data_sql, data_params)
                rows = cursor.fetchall()

                return {
                    'total': total,
                    'pageNum': page_num,
                    'pageSize': page_size,
                    'rows': rows
                }
        finally:
            conn.close()

    @staticmethod
    def check_product_permission(user_info, product_id):
        """检查用户是否有权限操作某个商品"""
        if user_info['role'] in SupplierService.GLOBAL_ROLES:
            return True

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                sql = "SELECT supplierId FROM py_product WHERE id = %s"
                cursor.execute(sql, (product_id,))
                result = cursor.fetchone()
                if not result:
                    return False
                return result['supplierId'] == user_info['id']
        finally:
            conn.close()
