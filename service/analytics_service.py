"""
数据分析服务
"""
from utils.db_utils import get_db_connection
from utils.response import success, error
from datetime import datetime, timedelta
import json


def _has_rows(rows):
    """判断查询结果是否为空"""
    return bool(rows and len(rows) > 0)


class AnalyticsService:
    """数据分析服务类"""
    
    def get_market_overview(self):
        """获取市场概览数据"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 总商品数
                    cursor.execute("SELECT COUNT(*) as total FROM py_product WHERE status = 1")
                    total_products = cursor.fetchone()['total']
                    
                    # 总订单数
                    cursor.execute("SELECT COUNT(*) as total FROM py_order WHERE status IN ('paid', 'shipped', 'completed')")
                    total_orders = cursor.fetchone()['total']
                    
                    # 总销售额
                    cursor.execute("SELECT IFNULL(SUM(payAmount), 0) as total FROM py_order WHERE status IN ('paid', 'shipped', 'completed')")
                    total_revenue = float(cursor.fetchone()['total'])
                    
                    # 活跃用户数
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
            print(f"获取市场概览失败: {e}")
            return error(f"获取市场概览失败: {str(e)}")
    
    def get_price_trend(self, days=30):
        """获取价格趋势"""
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
                    print(f"执行SQL: {sql}, 参数: {days}")
                    cursor.execute(sql, (days,))
                    rows = cursor.fetchall()
                    if not _has_rows(rows) and days < 180:
                        cursor.execute(sql, (180,))
                        rows = cursor.fetchall()
                    if not _has_rows(rows) and days < 180:
                        cursor.execute(sql, (180,))
                        rows = cursor.fetchall()
                    
                    dates = []
                    avg_prices = []
                    min_prices = []
                    max_prices = []
                    
                    for row in rows:
                        dates.append(row['date'].strftime('%Y-%m-%d'))
                        avg_prices.append(float(row['avgPrice']))
                        min_prices.append(float(row['minPrice']))
                        max_prices.append(float(row['maxPrice']))
                    
                    return success({
                        'dates': dates,
                        'avgPrices': avg_prices,
                        'minPrices': min_prices,
                        'maxPrices': max_prices
                    })
        except Exception as e:
            print(f"获取价格趋势失败: {e}")
            return error(f"获取价格趋势失败: {str(e)}")
    
    def get_hot_products(self, limit=10):
        """获取热门品种排行"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                        SELECT p.id, p.name, p.categoryId, c.name as categoryName,
                               COUNT(oi.id) as orderCount,
                               SUM(oi.quantity) as totalQuantity,
                               SUM(oi.totalAmount) as totalAmount
                        FROM py_product p
                        LEFT JOIN py_order_item oi ON p.id = oi.productId
                        LEFT JOIN py_order o ON oi.orderId = o.id
                        LEFT JOIN py_category c ON p.categoryId = c.id
                        WHERE o.status IN ('paid', 'shipped', 'completed')
                        AND o.createTime >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                        GROUP BY p.id
                        ORDER BY orderCount DESC
                        LIMIT %s
                    """
                    print(f"执行SQL: {sql}, 参数: {limit}")
                    cursor.execute(sql, (limit,))
                    rows = cursor.fetchall()
                    if not _has_rows(rows):
                        sql = """
                            SELECT p.id, p.name, p.categoryId, c.name as categoryName,
                                   COUNT(oi.id) as orderCount,
                                   SUM(oi.quantity) as totalQuantity,
                                   SUM(oi.totalAmount) as totalAmount
                            FROM py_product p
                            LEFT JOIN py_order_item oi ON p.id = oi.productId
                            LEFT JOIN py_order o ON oi.orderId = o.id
                            LEFT JOIN py_category c ON p.categoryId = c.id
                            WHERE o.status IN ('paid', 'shipped', 'completed')
                            GROUP BY p.id
                            ORDER BY orderCount DESC
                            LIMIT %s
                        """
                        cursor.execute(sql, (limit,))
                        rows = cursor.fetchall()
                    
                    products = []
                    for row in rows:
                        products.append({
                            'id': row['id'],
                            'name': row['name'],
                            'categoryName': row['categoryName'],
                            'orderCount': row['orderCount'],
                            'totalQuantity': row['totalQuantity'],
                            'totalAmount': float(row['totalAmount']) if row['totalAmount'] else 0
                        })
                    
                    return success(products)
        except Exception as e:
            print(f"获取热门品种失败: {e}")
            return error(f"获取热门品种失败: {str(e)}")
    
    def get_category_distribution(self):
        """获取分类分布"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                        SELECT c.name, COUNT(DISTINCT oi.id) as count
                        FROM py_category c
                        LEFT JOIN py_product p ON c.id = p.categoryId
                        LEFT JOIN py_order_item oi ON p.id = oi.productId
                        LEFT JOIN py_order o ON oi.orderId = o.id
                        WHERE o.status IN ('paid', 'shipped', 'completed')
                        AND o.createTime >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                        GROUP BY c.id
                        ORDER BY count DESC
                    """
                    print(f"执行SQL: {sql}")
                    cursor.execute(sql)
                    rows = cursor.fetchall()
                    if not _has_rows(rows):
                        sql = """
                            SELECT p1.name as product1, p2.name as product2, COUNT(*) as frequency
                            FROM py_order_item oi1
                            JOIN py_order_item oi2 ON oi1.orderId = oi2.orderId AND oi1.productId < oi2.productId
                            JOIN py_product p1 ON oi1.productId = p1.id
                            JOIN py_product p2 ON oi2.productId = p2.id
                            JOIN py_order o ON oi1.orderId = o.id
                            WHERE o.status IN ('paid', 'shipped', 'completed')
                            GROUP BY oi1.productId, oi2.productId
                            HAVING frequency > 1
                            ORDER BY frequency DESC
                            LIMIT 20
                        """
                        cursor.execute(sql)
                        rows = cursor.fetchall()
                    if not _has_rows(rows):
                        sql = """
                            SELECT p.id, p.name, 
                                   AVG(daily_sales.quantity) as avgDailyQuantity
                            FROM py_product p
                            LEFT JOIN (
                                SELECT oi.productId, DATE(o.createTime) as date, SUM(oi.quantity) as quantity
                                FROM py_order_item oi
                                JOIN py_order o ON oi.orderId = o.id
                                WHERE o.status IN ('paid', 'shipped', 'completed')
                                GROUP BY oi.productId, DATE(o.createTime)
                            ) daily_sales ON p.id = daily_sales.productId
                            GROUP BY p.id
                            HAVING avgDailyQuantity > 0
                            ORDER BY avgDailyQuantity DESC
                            LIMIT 10
                        """
                        cursor.execute(sql)
                        rows = cursor.fetchall()
                    if not _has_rows(rows):
                        sql = """
                            SELECT p.id, p.name, p.price as currentPrice,
                                   AVG(oi.price) as avgPrice,
                                   MIN(oi.price) as minPrice,
                                   MAX(oi.price) as maxPrice
                            FROM py_product p
                            LEFT JOIN py_order_item oi ON p.id = oi.productId
                            LEFT JOIN py_order o ON oi.orderId = o.id
                            WHERE o.status IN ('paid', 'shipped', 'completed')
                            GROUP BY p.id
                            HAVING COUNT(oi.id) > 0
                            ORDER BY MAX(oi.price) - MIN(oi.price) DESC
                            LIMIT 10
                        """
                        cursor.execute(sql)
                        rows = cursor.fetchall()
                    if not _has_rows(rows):
                        sql = """
                            SELECT c.name, COUNT(DISTINCT oi.id) as count
                            FROM py_category c
                            LEFT JOIN py_product p ON c.id = p.categoryId
                            LEFT JOIN py_order_item oi ON p.id = oi.productId
                            LEFT JOIN py_order o ON oi.orderId = o.id
                            WHERE o.status IN ('paid', 'shipped', 'completed')
                            GROUP BY c.id
                            ORDER BY count DESC
                        """
                        cursor.execute(sql)
                        rows = cursor.fetchall()
                    
                    data = []
                    for row in rows:
                        if row['count'] > 0:
                            data.append({
                                'name': row['name'],
                                'value': row['count']
                            })
                    
                    return success(data)
        except Exception as e:
            print(f"获取分类分布失败: {e}")
            return error(f"获取分类分布失败: {str(e)}")
    
    def get_sales_trend(self, days=30):
        """获取销售趋势"""
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
                    print(f"执行SQL: {sql}, 参数: {days}")
                    cursor.execute(sql, (days,))
                    rows = cursor.fetchall()
                    
                    dates = []
                    order_counts = []
                    revenues = []
                    
                    for row in rows:
                        dates.append(row['date'].strftime('%Y-%m-%d'))
                        order_counts.append(row['orderCount'])
                        revenues.append(float(row['revenue']))
                    
                    return success({
                        'dates': dates,
                        'orderCounts': order_counts,
                        'revenues': revenues
                    })
        except Exception as e:
            print(f"获取销售趋势失败: {e}")
            return error(f"获取销售趋势失败: {str(e)}")
    
    def get_inventory_alerts(self):
        """获取库存预警"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                        SELECT p.id, p.name, p.stock, p.categoryId, c.name as categoryName
                        FROM py_product p
                        LEFT JOIN py_category c ON p.categoryId = c.id
                        WHERE p.stock < 50 AND p.status = 1
                        ORDER BY p.stock ASC
                        LIMIT 20
                    """
                    print(f"执行SQL: {sql}")
                    cursor.execute(sql)
                    rows = cursor.fetchall()
                    
                    alerts = []
                    for row in rows:
                        level = 'danger' if row['stock'] < 20 else 'warning'
                        alerts.append({
                            'id': row['id'],
                            'name': row['name'],
                            'stock': row['stock'],
                            'categoryName': row['categoryName'],
                            'level': level
                        })
                    
                    return success(alerts)
        except Exception as e:
            print(f"获取库存预警失败: {e}")
            return error(f"获取库存预警失败: {str(e)}")
    
    def get_price_alerts(self):
        """获取价格异常预警"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 获取最近价格波动较大的商品
                    sql = """
                        SELECT p.id, p.name, p.price as currentPrice,
                               AVG(oi.price) as avgPrice,
                               MIN(oi.price) as minPrice,
                               MAX(oi.price) as maxPrice
                        FROM py_product p
                        LEFT JOIN py_order_item oi ON p.id = oi.productId
                        LEFT JOIN py_order o ON oi.orderId = o.id
                        WHERE o.createTime >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                        AND o.status IN ('paid', 'shipped', 'completed')
                        GROUP BY p.id
                        HAVING (MAX(oi.price) - MIN(oi.price)) / AVG(oi.price) > 0.2
                        ORDER BY (MAX(oi.price) - MIN(oi.price)) / AVG(oi.price) DESC
                        LIMIT 10
                    """
                    print(f"执行SQL: {sql}")
                    cursor.execute(sql)
                    rows = cursor.fetchall()
                    
                    alerts = []
                    for row in rows:
                        volatility = ((float(row['maxPrice']) - float(row['minPrice'])) / float(row['avgPrice'])) * 100
                        alerts.append({
                            'id': row['id'],
                            'name': row['name'],
                            'currentPrice': float(row['currentPrice']),
                            'avgPrice': float(row['avgPrice']),
                            'minPrice': float(row['minPrice']),
                            'maxPrice': float(row['maxPrice']),
                            'volatility': round(volatility, 2)
                        })
                    
                    return success(alerts)
        except Exception as e:
            print(f"获取价格预警失败: {e}")
            return error(f"获取价格预警失败: {str(e)}")
    
    def get_demand_forecast(self, days=7):
        """获取需求预测（基于历史数据的简单预测）"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 获取过去30天的销售数据
                    sql = """
                        SELECT p.id, p.name, 
                               AVG(daily_sales.quantity) as avgDailyQuantity
                        FROM py_product p
                        LEFT JOIN (
                            SELECT oi.productId, DATE(o.createTime) as date, SUM(oi.quantity) as quantity
                            FROM py_order_item oi
                            JOIN py_order o ON oi.orderId = o.id
                            WHERE o.createTime >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                            AND o.status IN ('paid', 'shipped', 'completed')
                            GROUP BY oi.productId, DATE(o.createTime)
                        ) daily_sales ON p.id = daily_sales.productId
                        GROUP BY p.id
                        HAVING avgDailyQuantity > 0
                        ORDER BY avgDailyQuantity DESC
                        LIMIT 10
                    """
                    print(f"执行SQL: {sql}")
                    cursor.execute(sql)
                    rows = cursor.fetchall()
                    
                    forecasts = []
                    for row in rows:
                        avg_daily = float(row['avgDailyQuantity'])
                        forecast = round(avg_daily * days)
                        forecasts.append({
                            'id': row['id'],
                            'name': row['name'],
                            'avgDailyQuantity': round(avg_daily, 2),
                            'forecastQuantity': forecast,
                            'forecastDays': days
                        })
                    
                    return success(forecasts)
        except Exception as e:
            print(f"获取需求预测失败: {e}")
            return error(f"获取需求预测失败: {str(e)}")
    
    def get_product_association(self):
        """获取商品关联分析"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 查找经常一起购买的商品
                    sql = """
                        SELECT p1.name as product1, p2.name as product2, COUNT(*) as frequency
                        FROM py_order_item oi1
                        JOIN py_order_item oi2 ON oi1.orderId = oi2.orderId AND oi1.productId < oi2.productId
                        JOIN py_product p1 ON oi1.productId = p1.id
                        JOIN py_product p2 ON oi2.productId = p2.id
                        JOIN py_order o ON oi1.orderId = o.id
                        WHERE o.createTime >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                        AND o.status IN ('paid', 'shipped', 'completed')
                        GROUP BY oi1.productId, oi2.productId
                        HAVING frequency > 1
                        ORDER BY frequency DESC
                        LIMIT 20
                    """
                    print(f"执行SQL: {sql}")
                    cursor.execute(sql)
                    rows = cursor.fetchall()
                    
                    associations = []
                    for row in rows:
                        associations.append({
                            'product1': row['product1'],
                            'product2': row['product2'],
                            'frequency': row['frequency']
                        })
                    
                    return success(associations)
        except Exception as e:
            print(f"获取商品关联分析失败: {e}")
            return error(f"获取商品关联分析失败: {str(e)}")
    
    def get_regional_sales(self):
        """获取区域销售分布"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                        SELECT receiverProvince as province,
                               COUNT(*) as orderCount,
                               SUM(payAmount) as revenue
                        FROM py_order
                        WHERE status IN ('paid', 'shipped', 'completed')
                        AND createTime >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                        GROUP BY receiverProvince
                        ORDER BY revenue DESC
                        LIMIT 20
                    """
                    print(f"执行SQL: {sql}")
                    cursor.execute(sql)
                    rows = cursor.fetchall()
                    
                    regions = []
                    for row in rows:
                        regions.append({
                            'province': row['province'],
                            'orderCount': row['orderCount'],
                            'revenue': float(row['revenue'])
                        })
                    
                    return success(regions)
        except Exception as e:
            print(f"获取区域销售分布失败: {e}")
            return error(f"获取区域销售分布失败: {str(e)}")

    # ----------------------------------------------------------------
    # 运营统计报告专属接口
    # ----------------------------------------------------------------

    def get_product_price_distribution(self):
        """商品分布与价格区间分析"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 1. 各品类商品数量分布
                    cursor.execute("""
                        SELECT c.name AS category,
                               COUNT(p.id) AS productCount,
                               ROUND(AVG(p.price), 2) AS avgPrice,
                               MIN(p.price) AS minPrice,
                               MAX(p.price) AS maxPrice,
                               SUM(p.sales) AS totalSales
                        FROM py_product p
                        JOIN py_category c ON p.categoryId = c.id
                        WHERE p.status = 1
                        GROUP BY c.id, c.name
                        ORDER BY productCount DESC
                        LIMIT 12
                    """)
                    category_dist = cursor.fetchall()

                    # 2. 价格区间分布（商品数量）
                    cursor.execute("""
                        SELECT
                            CASE
                                WHEN price < 50   THEN '0-50元'
                                WHEN price < 100  THEN '50-100元'
                                WHEN price < 200  THEN '100-200元'
                                WHEN price < 500  THEN '200-500元'
                                WHEN price < 1000 THEN '500-1000元'
                                ELSE '1000元以上'
                            END AS priceRange,
                            COUNT(*) AS cnt
                        FROM py_product
                        WHERE status = 1
                        GROUP BY priceRange
                        ORDER BY MIN(price)
                    """)
                    price_ranges = cursor.fetchall()

                    # 3. 热销 vs 库存预警（气泡数据：x=价格, y=销量, size=库存）
                    cursor.execute("""
                        SELECT p.name, p.price, p.sales, p.stock,
                               c.name AS category
                        FROM py_product p
                        JOIN py_category c ON p.categoryId = c.id
                        WHERE p.status = 1 AND p.sales > 0
                        ORDER BY p.sales DESC
                        LIMIT 20
                    """)
                    bubble_data = cursor.fetchall()

                    return success({
                        'categoryDist': [
                            {'name': r['category'], 'value': r['productCount'],
                             'avgPrice': float(r['avgPrice']),
                             'minPrice': float(r['minPrice']),
                             'maxPrice': float(r['maxPrice']),
                             'totalSales': float(r['totalSales']) if r['totalSales'] is not None else 0}
                            for r in category_dist
                        ],
                        'priceRanges': [
                            {'range': r['priceRange'], 'count': r['cnt']}
                            for r in price_ranges
                        ],
                        'bubbleData': [
                            {'name': r['name'], 'price': float(r['price']),
                             'sales': float(r['sales']) if r['sales'] is not None else 0,
                             'stock': int(r['stock']) if r['stock'] is not None else 0,
                             'category': r['category']}
                            for r in bubble_data
                        ]
                    })
        except Exception as e:
            print(f"商品分布与价格区间分析失败: {e}")
            return error(str(e))

    def get_review_summary(self):
        """用户评价汇总分析"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 1. 总体评分分布（1-5星各多少）
                    cursor.execute("""
                        SELECT reviewRating AS rating, COUNT(*) AS cnt
                        FROM py_order_item
                        WHERE reviewRating IS NOT NULL
                        GROUP BY reviewRating
                        ORDER BY reviewRating
                    """)
                    rating_dist = {str(r['rating']): r['cnt'] for r in cursor.fetchall()}

                    # 2. 各品类平均评分
                    cursor.execute("""
                        SELECT c.name AS category,
                               ROUND(AVG(oi.reviewRating), 2) AS avgRating,
                               COUNT(oi.id) AS reviewCount
                        FROM py_order_item oi
                        JOIN py_product p ON oi.productId = p.id
                        JOIN py_category c ON p.categoryId = c.id
                        WHERE oi.reviewRating IS NOT NULL
                        GROUP BY c.id, c.name
                        HAVING reviewCount >= 1
                        ORDER BY avgRating DESC
                    """)
                    category_ratings = cursor.fetchall()

                    # 3. 评价词条TOP标签（来自 py_product_review_tags，表不存在时返回空）
                    try:
                        cursor.execute("""
                            SELECT tagName, tagCategory, SUM(tagCount) AS total
                            FROM py_product_review_tags
                            GROUP BY tagName, tagCategory
                            ORDER BY total DESC
                            LIMIT 30
                        """)
                        tag_rows = cursor.fetchall()
                    except Exception:
                        tag_rows = []

                    # 4. 月度评价趋势（近6个月）
                    cursor.execute("""
                        SELECT DATE_FORMAT(STR_TO_DATE(reviewTime,'%%Y-%%m-%%d'), '%%Y-%%m') AS month,
                               COUNT(*) AS cnt,
                               ROUND(AVG(reviewRating), 2) AS avgRating
                        FROM py_order_item
                        WHERE reviewRating IS NOT NULL
                          AND reviewTime IS NOT NULL
                          AND STR_TO_DATE(reviewTime,'%%Y-%%m-%%d') >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
                        GROUP BY month
                        ORDER BY month
                    """)
                    monthly = cursor.fetchall()

                    # 好评率
                    total_reviews = sum(int(v) for v in rating_dist.values())
                    good_reviews = int(rating_dist.get('4', 0)) + int(rating_dist.get('5', 0))
                    good_rate = round(good_reviews / total_reviews * 100, 1) if total_reviews else 0

                    return success({
                        'totalReviews': total_reviews,
                        'goodRate': good_rate,
                        'ratingDist': [
                            {'star': i, 'count': int(rating_dist.get(str(i), 0))}
                            for i in range(1, 6)
                        ],
                        'categoryRatings': [
                            {'category': r['category'],
                             'avgRating': float(r['avgRating']),
                             'reviewCount': r['reviewCount']}
                            for r in category_ratings
                        ],
                        'topTags': [
                            {'name': r['tagName'], 'category': r['tagCategory'],
                             'value': r['total']}
                            for r in tag_rows
                        ],
                        'monthly': [
                            {'month': r['month'], 'count': r['cnt'],
                             'avgRating': float(r['avgRating'])}
                            for r in monthly
                        ]
                    })
        except Exception as e:
            print(f"用户评价汇总分析失败: {e}")
            return error(str(e))

    def get_category_competition(self):
        """品类竞争格局分析"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 1. 各品类销售额占比（近30天）
                    cursor.execute("""
                        SELECT c.name AS category,
                               COALESCE(SUM(oi.totalAmount), 0) AS revenue,
                               COALESCE(SUM(oi.quantity), 0) AS quantity,
                               COUNT(DISTINCT oi.orderId) AS orderCount,
                               COUNT(DISTINCT p.id) AS productCount
                        FROM py_category c
                        LEFT JOIN py_product p ON c.id = p.categoryId AND p.status = 1
                        LEFT JOIN py_order_item oi ON p.id = oi.productId
                        LEFT JOIN py_order o ON oi.orderId = o.id
                            AND o.status IN ('paid','shipped','completed')
                            AND o.createTime >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                        GROUP BY c.id, c.name
                        HAVING productCount > 0
                        ORDER BY revenue DESC
                    """)
                    competition = cursor.fetchall()

                    # 2. 各品类商家数（卖家竞争度）
                    cursor.execute("""
                        SELECT c.name AS category,
                               COUNT(DISTINCT p.supplierId) AS supplierCount
                        FROM py_category c
                        JOIN py_product p ON c.id = p.categoryId AND p.status = 1
                        GROUP BY c.id, c.name
                    """)
                    supplier_comp = {r['category']: r['supplierCount'] for r in cursor.fetchall()}

                    # 3. 品类价格带雷达（均价/最高/最低）
                    cursor.execute("""
                        SELECT c.name AS category,
                               ROUND(AVG(p.price),2) AS avgPrice,
                               ROUND(AVG(p.sales),2) AS avgSales,
                               ROUND(AVG(IFNULL(oi_r.avgRating,0)),2) AS avgRating
                        FROM py_category c
                        JOIN py_product p ON c.id = p.categoryId AND p.status = 1
                        LEFT JOIN (
                            SELECT productId, AVG(reviewRating) AS avgRating
                            FROM py_order_item
                            WHERE reviewRating IS NOT NULL
                            GROUP BY productId
                        ) oi_r ON p.id = oi_r.productId
                        GROUP BY c.id, c.name
                        ORDER BY avgSales DESC
                        LIMIT 8
                    """)
                    radar_raw = cursor.fetchall()

                    result = []
                    for r in competition:
                        result.append({
                            'category': r['category'],
                            'revenue': float(r['revenue']),
                            'quantity': int(r['quantity']),
                            'orderCount': int(r['orderCount']),
                            'productCount': int(r['productCount']),
                            'supplierCount': supplier_comp.get(r['category'], 0)
                        })

                    return success({
                        'competition': result,
                        'radarData': [
                            {'category': r['category'],
                             'avgPrice': float(r['avgPrice']),
                             'avgSales': float(r['avgSales']),
                             'avgRating': float(r['avgRating'])}
                            for r in radar_raw
                        ]
                    })
        except Exception as e:
            print(f"品类竞争格局分析失败: {e}")
            return error(str(e))

    # ----------------------------------------------------------------
    # 商家专属销售分析（数据隔离：仅查自己的商品/订单）
    # ----------------------------------------------------------------

    def supplier_overview(self, supplier_id):
        """商家销售概览"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # 在售商品数
                    cur.execute("SELECT COUNT(*) AS cnt FROM py_product WHERE supplierId=%s AND status=1", [supplier_id])
                    product_count = cur.fetchone()['cnt']

                    # 总订单数 & 总销售额（近30天 / 全部）
                    cur.execute("""
                        SELECT COUNT(*) AS total_orders,
                               COALESCE(SUM(payAmount),0) AS total_revenue,
                               COUNT(DISTINCT userId) AS customer_count
                        FROM py_order
                        WHERE supplierId=%s AND status IN ('paid','shipped','delivered','completed')
                    """, [supplier_id])
                    row = cur.fetchone()

                    # 近30天
                    cur.execute("""
                        SELECT COUNT(*) AS orders_30,
                               COALESCE(SUM(payAmount),0) AS revenue_30
                        FROM py_order
                        WHERE supplierId=%s AND status IN ('paid','shipped','delivered','completed')
                          AND createTime >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                    """, [supplier_id])
                    r30 = cur.fetchone()

                    # 待处理订单
                    cur.execute("SELECT COUNT(*) AS pending FROM py_order WHERE supplierId=%s AND status='paid'", [supplier_id])
                    pending = cur.fetchone()['pending']

                    # 好评率
                    cur.execute("""
                        SELECT COUNT(*) AS total,
                               SUM(CASE WHEN oi.reviewRating >= 4 THEN 1 ELSE 0 END) AS good
                        FROM py_order_item oi
                        JOIN py_order o ON oi.orderId=o.id
                        WHERE o.supplierId=%s AND oi.reviewRating IS NOT NULL
                    """, [supplier_id])
                    rv = cur.fetchone()
                    good_rate = round(rv['good'] / rv['total'] * 100, 1) if rv['total'] else 0

                    return success({
                        'productCount':  product_count,
                        'totalOrders':   row['total_orders'],
                        'totalRevenue':  float(row['total_revenue']),
                        'customerCount': row['customer_count'],
                        'orders30':      r30['orders_30'],
                        'revenue30':     float(r30['revenue_30']),
                        'pendingOrders': pending,
                        'goodRate':      good_rate
                    })
        except Exception as e:
            print(f"商家概览失败: {e}")
            return error(str(e))

    def supplier_sales_trend(self, supplier_id, days=30):
        """商家销售趋势（近N天）"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT DATE(createTime) AS date,
                               COUNT(*) AS orderCount,
                               COALESCE(SUM(payAmount),0) AS revenue
                        FROM py_order
                        WHERE supplierId=%s AND status IN ('paid','shipped','delivered','completed')
                          AND createTime >= DATE_SUB(NOW(), INTERVAL %s DAY)
                        GROUP BY DATE(createTime)
                        ORDER BY DATE(createTime)
                    """, [supplier_id, days])
                    rows = cur.fetchall()
                    dates, counts, revenues = [], [], []
                    for r in rows:
                        dt = r['date']
                        dates.append(dt.strftime('%m-%d') if hasattr(dt,'strftime') else str(dt)[:10])
                        counts.append(r['orderCount'])
                        revenues.append(float(r['revenue']))
                    return success({'dates': dates, 'orderCounts': counts, 'revenues': revenues})
        except Exception as e:
            print(f"商家销售趋势失败: {e}")
            return error(str(e))

    def supplier_product_rank(self, supplier_id, limit=10):
        """商家商品销量排行"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT p.id, p.name, p.price, p.stock,
                               COALESCE(SUM(oi.quantity),0)   AS totalQty,
                               COALESCE(SUM(oi.totalAmount),0) AS totalAmt,
                               COUNT(DISTINCT o.id)            AS orderCount,
                               ROUND(AVG(oi.reviewRating),2)   AS avgRating,
                               COUNT(oi.reviewRating)          AS reviewCount
                        FROM py_product p
                        LEFT JOIN py_order_item oi ON p.id=oi.productId
                        LEFT JOIN py_order o ON oi.orderId=o.id
                            AND o.status IN ('paid','shipped','delivered','completed')
                        WHERE p.supplierId=%s AND p.status=1
                        GROUP BY p.id
                        ORDER BY totalQty DESC
                        LIMIT %s
                    """, [supplier_id, limit])
                    rows = cur.fetchall()
                    return success([{
                        'id': r['id'], 'name': r['name'],
                        'price': float(r['price']),
                        'stock': r['stock'],
                        'totalQty': int(r['totalQty']),
                        'totalAmt': float(r['totalAmt']),
                        'orderCount': int(r['orderCount']),
                        'avgRating': float(r['avgRating']) if r['avgRating'] else None,
                        'reviewCount': int(r['reviewCount'])
                    } for r in rows])
        except Exception as e:
            print(f"商家商品排行失败: {e}")
            return error(str(e))

    def supplier_category_sales(self, supplier_id):
        """商家各品类销售占比"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT c.name AS category,
                               COALESCE(SUM(oi.totalAmount),0) AS revenue,
                               COALESCE(SUM(oi.quantity),0)    AS qty
                        FROM py_product p
                        JOIN py_category c ON p.categoryId=c.id
                        LEFT JOIN py_order_item oi ON p.id=oi.productId
                        LEFT JOIN py_order o ON oi.orderId=o.id
                            AND o.status IN ('paid','shipped','delivered','completed')
                        WHERE p.supplierId=%s AND p.status=1
                        GROUP BY c.id, c.name
                        ORDER BY revenue DESC
                    """, [supplier_id])
                    rows = cur.fetchall()
                    return success([{
                        'name': r['category'],
                        'value': float(r['revenue']),
                        'qty': int(r['qty'])
                    } for r in rows])
        except Exception as e:
            print(f"商家品类销售失败: {e}")
            return error(str(e))

    def supplier_review_analysis(self, supplier_id):
        """商家顾客评价分析"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # 评分分布
                    cur.execute("""
                        SELECT oi.reviewRating AS rating, COUNT(*) AS cnt
                        FROM py_order_item oi
                        JOIN py_order o ON oi.orderId=o.id
                        WHERE o.supplierId=%s AND oi.reviewRating IS NOT NULL
                        GROUP BY oi.reviewRating ORDER BY oi.reviewRating
                    """, [supplier_id])
                    dist = {str(r['rating']): r['cnt'] for r in cur.fetchall()}

                    # 各商品平均评分（评价>=1）
                    cur.execute("""
                        SELECT p.name,
                               ROUND(AVG(oi.reviewRating),2) AS avgRating,
                               COUNT(*) AS cnt
                        FROM py_order_item oi
                        JOIN py_order o ON oi.orderId=o.id
                        JOIN py_product p ON oi.productId=p.id
                        WHERE o.supplierId=%s AND oi.reviewRating IS NOT NULL
                        GROUP BY p.id HAVING cnt>=1
                        ORDER BY avgRating DESC LIMIT 12
                    """, [supplier_id])
                    product_ratings = cur.fetchall()

                    # 月度评价趋势
                    cur.execute("""
                        SELECT DATE_FORMAT(STR_TO_DATE(oi.reviewTime,'%%Y-%%m-%%d'),'%%Y-%%m') AS month,
                               COUNT(*) AS cnt,
                               ROUND(AVG(oi.reviewRating),2) AS avgRating
                        FROM py_order_item oi
                        JOIN py_order o ON oi.orderId=o.id
                        WHERE o.supplierId=%s AND oi.reviewRating IS NOT NULL
                          AND oi.reviewTime IS NOT NULL
                          AND STR_TO_DATE(oi.reviewTime,'%%Y-%%m-%%d') >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
                        GROUP BY month ORDER BY month
                    """, [supplier_id])
                    monthly = cur.fetchall()

                    # 评价词云标签（来自该商家商品的 review tags）
                    cur.execute("""
                        SELECT t.tagName, SUM(t.tagCount) AS total, t.tagCategory
                        FROM py_product_review_tags t
                        JOIN py_product p ON t.productId = p.id
                        WHERE p.supplierId = %s AND t.tagName IS NOT NULL AND t.tagCount > 0
                        GROUP BY t.tagName, t.tagCategory
                        ORDER BY total DESC
                        LIMIT 60
                    """, [supplier_id])
                    tag_rows = cur.fetchall()

                    total = sum(int(v) for v in dist.values())
                    good  = int(dist.get('4',0)) + int(dist.get('5',0))
                    return success({
                        'totalReviews': total,
                        'goodRate': round(good/total*100,1) if total else 0,
                        'ratingDist': [{'star': i, 'count': int(dist.get(str(i),0))} for i in range(1,6)],
                        'productRatings': [{'name': r['name'], 'avgRating': float(r['avgRating']), 'cnt': r['cnt']} for r in product_ratings],
                        'monthly': [{'month': r['month'], 'count': r['cnt'], 'avgRating': float(r['avgRating'])} for r in monthly],
                        'topTags': [{'name': r['tagName'], 'value': int(r['total']), 'category': r['tagCategory']} for r in tag_rows]
                    })
        except Exception as e:
            print(f"商家评价分析失败: {e}")
            return error(str(e))

    def supplier_inventory_alert(self, supplier_id):
        """商家库存预警（仅自己的商品）"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT p.id, p.name, p.price, p.stock, c.name AS category
                        FROM py_product p
                        JOIN py_category c ON p.categoryId=c.id
                        WHERE p.supplierId=%s AND p.status=1 AND p.stock < 50
                        ORDER BY p.stock ASC LIMIT 20
                    """, [supplier_id])
                    rows = cur.fetchall()
                    return success([{
                        'id': r['id'], 'name': r['name'],
                        'price': float(r['price']), 'stock': r['stock'],
                        'category': r['category'],
                        'level': 'danger' if r['stock'] < 10 else 'warning'
                    } for r in rows])
        except Exception as e:
            print(f"商家库存预警失败: {e}")
            return error(str(e))

