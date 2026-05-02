from service.analytics_service import AnalyticsService as BaseAnalyticsService
from utils.db_utils import get_db_connection
from utils.response import success, error


def _has_rows(rows):
    return bool(rows and len(rows) > 0)


class AnalyticsService(BaseAnalyticsService):
    """修正版分析服务，补充空数据回退逻辑"""

    def get_market_overview(self):
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) as total FROM py_product WHERE status = 1")
                    total_products = cursor.fetchone()['total']

                    cursor.execute("SELECT COUNT(*) as total FROM py_order WHERE status IN ('paid', 'shipped', 'completed')")
                    total_orders = cursor.fetchone()['total']

                    cursor.execute("SELECT IFNULL(SUM(payAmount), 0) as total FROM py_order WHERE status IN ('paid', 'shipped', 'completed')")
                    total_revenue = float(cursor.fetchone()['total'])

                    cursor.execute("SELECT COUNT(DISTINCT userId) as total FROM py_order WHERE createTime >= DATE_SUB(NOW(), INTERVAL 30 DAY)")
                    active_users = cursor.fetchone()['total']
                    if not active_users:
                        cursor.execute("SELECT COUNT(DISTINCT userId) as total FROM py_order WHERE createTime >= DATE_SUB(NOW(), INTERVAL 180 DAY)")
                        active_users = cursor.fetchone()['total']

                    return success({
                        'totalProducts': total_products,
                        'totalOrders': total_orders,
                        'totalRevenue': round(total_revenue, 2),
                        'activeUsers': active_users
                    })
        except Exception as e:
            return error(f"获取市场概览失败: {str(e)}")

    def get_price_trend(self, days=30):
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                        SELECT DATE(o.createTime) as date,
                               AVG(oi.price) as avgPrice,
                               MIN(oi.price) as minPrice,
                               MAX(oi.price) as maxPrice
                        FROM py_order o
                        JOIN py_order_item oi ON o.id = oi.orderId
                        WHERE o.createTime >= DATE_SUB(NOW(), INTERVAL %s DAY)
                        AND o.status IN ('paid', 'shipped', 'completed')
                        GROUP BY DATE(o.createTime)
                        ORDER BY date
                    """
                    cursor.execute(sql, (days,))
                    rows = cursor.fetchall()
                    if not _has_rows(rows) and days < 180:
                        cursor.execute(sql, (180,))
                        rows = cursor.fetchall()

                    return success({
                        'dates': [row['date'].strftime('%Y-%m-%d') for row in rows],
                        'avgPrices': [float(row['avgPrice']) for row in rows],
                        'minPrices': [float(row['minPrice']) for row in rows],
                        'maxPrices': [float(row['maxPrice']) for row in rows]
                    })
        except Exception as e:
            return error(f"获取价格趋势失败: {str(e)}")

    def get_hot_products(self, limit=10):
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                        SELECT p.id, p.name, c.name as categoryName,
                               COUNT(oi.id) as orderCount,
                               SUM(oi.quantity) as totalQuantity,
                               SUM(oi.totalAmount) as totalAmount
                        FROM py_product p
                        LEFT JOIN py_order_item oi ON p.id = oi.productId
                        LEFT JOIN py_order o ON oi.orderId = o.id
                        LEFT JOIN py_category c ON p.categoryId = c.id
                        WHERE o.status IN ('paid', 'shipped', 'completed')
                        AND o.createTime >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                        GROUP BY p.id, p.name, c.name
                        ORDER BY orderCount DESC
                        LIMIT %s
                    """
                    cursor.execute(sql, (limit,))
                    rows = cursor.fetchall()
                    if not _has_rows(rows):
                        sql = """
                            SELECT p.id, p.name, c.name as categoryName,
                                   COUNT(oi.id) as orderCount,
                                   SUM(oi.quantity) as totalQuantity,
                                   SUM(oi.totalAmount) as totalAmount
                            FROM py_product p
                            LEFT JOIN py_order_item oi ON p.id = oi.productId
                            LEFT JOIN py_order o ON oi.orderId = o.id
                            LEFT JOIN py_category c ON p.categoryId = c.id
                            WHERE o.status IN ('paid', 'shipped', 'completed')
                            GROUP BY p.id, p.name, c.name
                            ORDER BY orderCount DESC
                            LIMIT %s
                        """
                        cursor.execute(sql, (limit,))
                        rows = cursor.fetchall()

                    return success([{
                        'id': row['id'],
                        'name': row['name'],
                        'categoryName': row['categoryName'],
                        'orderCount': row['orderCount'],
                        'totalQuantity': row['totalQuantity'],
                        'totalAmount': float(row['totalAmount']) if row['totalAmount'] else 0
                    } for row in rows])
        except Exception as e:
            return error(f"获取热门商品失败: {str(e)}")

    def get_category_distribution(self):
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                        SELECT c.name AS name, COUNT(DISTINCT oi.id) AS total_count
                        FROM py_category c
                        LEFT JOIN py_product p ON c.id = p.categoryId
                        LEFT JOIN py_order_item oi ON p.id = oi.productId
                        LEFT JOIN py_order o ON oi.orderId = o.id
                        WHERE o.status IN ('paid', 'shipped', 'completed')
                        AND o.createTime >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                        GROUP BY c.id, c.name
                        ORDER BY total_count DESC
                    """
                    cursor.execute(sql)
                    rows = cursor.fetchall()
                    if not _has_rows(rows):
                        sql = """
                            SELECT c.name AS name, COUNT(DISTINCT oi.id) AS total_count
                            FROM py_category c
                            LEFT JOIN py_product p ON c.id = p.categoryId
                            LEFT JOIN py_order_item oi ON p.id = oi.productId
                            LEFT JOIN py_order o ON oi.orderId = o.id
                            WHERE o.status IN ('paid', 'shipped', 'completed')
                            GROUP BY c.id, c.name
                            ORDER BY total_count DESC
                        """
                        cursor.execute(sql)
                        rows = cursor.fetchall()

                    return success([{
                        'name': row['name'],
                        'value': row['total_count']
                    } for row in rows if row['total_count'] > 0])
        except Exception as e:
            return error(f"获取分类分布失败: {str(e)}")

    def get_sales_trend(self, days=30):
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                        SELECT DATE(createTime) as date,
                               COUNT(*) as orderCount,
                               SUM(payAmount) as revenue
                        FROM py_order
                        WHERE createTime >= DATE_SUB(NOW(), INTERVAL %s DAY)
                        AND status IN ('paid', 'shipped', 'completed')
                        GROUP BY DATE(createTime)
                        ORDER BY date
                    """
                    cursor.execute(sql, (days,))
                    rows = cursor.fetchall()
                    if not _has_rows(rows) and days < 180:
                        cursor.execute(sql, (180,))
                        rows = cursor.fetchall()

                    return success({
                        'dates': [row['date'].strftime('%Y-%m-%d') for row in rows],
                        'orderCounts': [row['orderCount'] for row in rows],
                        'revenues': [float(row['revenue']) for row in rows]
                    })
        except Exception as e:
            return error(f"获取销售趋势失败: {str(e)}")

    def get_price_alerts(self):
        result = super().get_price_alerts()
        if isinstance(result, dict) and result.get('code') == 200 and not result.get('data'):
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        sql = """
                            SELECT p.id, p.name, p.price as currentPrice,
                                   AVG(oi.price) as avgPrice,
                                   MIN(oi.price) as minPrice,
                                   MAX(oi.price) as maxPrice
                            FROM py_product p
                            LEFT JOIN py_order_item oi ON p.id = oi.productId
                            LEFT JOIN py_order o ON oi.orderId = o.id
                            WHERE o.status IN ('paid', 'shipped', 'completed')
                            GROUP BY p.id, p.name, p.price
                            HAVING COUNT(oi.id) > 0
                            ORDER BY MAX(oi.price) - MIN(oi.price) DESC
                            LIMIT 10
                        """
                        cursor.execute(sql)
                        rows = cursor.fetchall()
                        return success([{
                            'id': row['id'],
                            'name': row['name'],
                            'currentPrice': float(row['currentPrice']),
                            'avgPrice': float(row['avgPrice']),
                            'minPrice': float(row['minPrice']),
                            'maxPrice': float(row['maxPrice']),
                            'volatility': round(((float(row['maxPrice']) - float(row['minPrice'])) / float(row['avgPrice'])) * 100, 2) if row['avgPrice'] else 0
                        } for row in rows])
            except Exception as e:
                return error(f"获取价格预警失败: {str(e)}")
        return result

    def get_demand_forecast(self, days=7):
        result = super().get_demand_forecast(days)
        if isinstance(result, dict) and result.get('code') == 200 and not result.get('data'):
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        sql = """
                            SELECT p.id, p.name, AVG(daily_sales.quantity) as avgDailyQuantity
                            FROM py_product p
                            LEFT JOIN (
                                SELECT oi.productId, DATE(o.createTime) as date, SUM(oi.quantity) as quantity
                                FROM py_order_item oi
                                JOIN py_order o ON oi.orderId = o.id
                                WHERE o.status IN ('paid', 'shipped', 'completed')
                                GROUP BY oi.productId, DATE(o.createTime)
                            ) daily_sales ON p.id = daily_sales.productId
                            GROUP BY p.id, p.name
                            HAVING avgDailyQuantity > 0
                            ORDER BY avgDailyQuantity DESC
                            LIMIT 10
                        """
                        cursor.execute(sql)
                        rows = cursor.fetchall()
                        return success([{
                            'id': row['id'],
                            'name': row['name'],
                            'avgDailyQuantity': round(float(row['avgDailyQuantity']), 2),
                            'forecastQuantity': round(float(row['avgDailyQuantity']) * days),
                            'forecastDays': days
                        } for row in rows])
            except Exception as e:
                return error(f"获取需求预测失败: {str(e)}")
        return result

    def get_product_association(self):
        result = super().get_product_association()
        if isinstance(result, dict) and result.get('code') == 200 and not result.get('data'):
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        sql = """
                            SELECT p1.name as product1, p2.name as product2, COUNT(*) as frequency
                            FROM py_order_item oi1
                            JOIN py_order_item oi2 ON oi1.orderId = oi2.orderId AND oi1.productId < oi2.productId
                            JOIN py_product p1 ON oi1.productId = p1.id
                            JOIN py_product p2 ON oi2.productId = p2.id
                            JOIN py_order o ON oi1.orderId = o.id
                            WHERE o.status IN ('paid', 'shipped', 'completed')
                            GROUP BY oi1.productId, oi2.productId, p1.name, p2.name
                            HAVING frequency > 1
                            ORDER BY frequency DESC
                            LIMIT 20
                        """
                        cursor.execute(sql)
                        rows = cursor.fetchall()
                        return success([{
                            'product1': row['product1'],
                            'product2': row['product2'],
                            'frequency': row['frequency']
                        } for row in rows])
            except Exception as e:
                return error(f"获取商品关联分析失败: {str(e)}")
        return result
