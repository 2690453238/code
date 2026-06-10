"""
商品服务层
"""
from typing import Any, Dict, List, Optional, Tuple
from model.mall.product_model import ProductModel
from utils.db_utils import get_db_connection
from utils.response import success, error, page_response


class ProductService:
    """商品服务"""

    VALID_ORDER_STATUS: Tuple[str, ...] = ('paid', 'shipped', 'delivered', 'completed')
    
    def __init__(self):
        self.db = None
        self.product_model = None

    def _ensure_db(self):
        """确保数据库连接有效，如连接过期则自动重连"""
        try:
            if self.db is not None:
                self.db.ping(reconnect=True)
                return
        except:
            pass
        try:
            if self.db is not None:
                self.db.close()
        except:
            pass
        self.db = get_db_connection()
        self.product_model = ProductModel(self.db)

    def get_products(self, category_id: int = None, status: int = None, page: int = 1, limit: int = 10, keyword: str = None, sort_type: str = 'default') -> Dict:
        """获取商品列表"""
        try:
            self._ensure_db()
            result = self.product_model.get_products(category_id, status, page, limit, keyword, sort_type)
            return page_response(result['rows'], result['total'], result['page'], result['limit'])
        except Exception as e:
            print(f"获取商品列表失败: {str(e)}")
            return error("获取商品列表失败")
    
    def get_product_by_id(self, product_id: int) -> Dict:
        """根据ID获取商品详情"""
        try:
            self._ensure_db()
            product = self.product_model.get_product_by_id(product_id)
            if not product:
                return error("商品不存在")
            
            # 获取评价统计信息
            review_stats = self.get_product_review_stats(product_id)
            if review_stats['code'] == 200:
                product['reviewStats'] = review_stats['data']
            else:
                product['reviewStats'] = {
                    'totalReviews': 0,
                    'averageRating': 0,
                    'ratingDistribution': {
                        'five': 0, 'four': 0, 'three': 0, 'two': 0, 'one': 0
                    }
                }
            
            return success(product)
        except Exception as e:
            print(f"获取商品详情失败: {str(e)}")
            return error("获取商品详情失败")
    
    def create_product(self, product_data: Dict) -> Dict:
        """创建商品"""
        try:
            self._ensure_db()
            # 验证必填字段
            required_fields = ['name', 'categoryId', 'price']
            for field in required_fields:
                if field not in product_data or not product_data[field]:
                    return error(f"{field}不能为空")
            
            product_id = self.product_model.create_product(product_data)
            return success({"id": product_id}, "商品创建成功")
        except Exception as e:
            print(f"创建商品失败: {str(e)}")
            return error("创建商品失败")
    
    def update_product(self, product_id: int, product_data: Dict) -> Dict:
        """更新商品"""
        try:
            self._ensure_db()
            result = self.product_model.update_product(product_id, product_data)
            if result:
                return success(None, "商品更新成功")
            else:
                return error("商品更新失败")
        except Exception as e:
            print(f"更新商品失败: {str(e)}")
            return error("更新商品失败")
    
    def delete_product(self, product_id: int) -> Dict:
        """删除商品"""
        try:
            self._ensure_db()
            result = self.product_model.delete_product(product_id)
            if result:
                return success(None, "商品删除成功")
            else:
                return error("商品删除失败")
        except Exception as e:
            print(f"删除商品失败: {str(e)}")
            return error("删除商品失败")
    
    def get_hot_products(self, limit: int = 10) -> Dict:
        """获取热门商品"""
        try:
            self._ensure_db()
            result = self.product_model.get_products(status=1, limit=limit)
            # 过滤热门商品
            hot_products = [p for p in result['rows'] if p.get('isHot') == 1]
            return success(hot_products)
        except Exception as e:
            print(f"获取热门商品失败: {str(e)}")
            return error("获取热门商品失败")
    
    def get_new_products(self, limit: int = 10) -> Dict:
        """获取新品商品"""
        try:
            self._ensure_db()
            result = self.product_model.get_products(status=1, limit=limit)
            # 过滤新品商品
            new_products = [p for p in result['rows'] if p.get('isNew') == 1]
            return success(new_products)
        except Exception as e:
            print(f"获取新品商品失败: {str(e)}")
            return error("获取新品商品失败")
    
    def update_product_status(self, product_id: int, status: int) -> Dict:
        """更新商品状态"""
        try:
            self._ensure_db()
            result = self.product_model.update_product_status(product_id, status)
            if result:
                status_text = "上架" if status == 1 else "下架"
                return success(None, f"商品{status_text}成功")
            else:
                return error("商品状态更新失败")
        except Exception as e:
            print(f"更新商品状态失败: {str(e)}")
            return error("更新商品状态失败")
    
    def batch_delete_products(self, product_ids: List[int]) -> Dict:
        """批量删除商品"""
        try:
            self._ensure_db()
            result = self.product_model.batch_delete_products(product_ids)
            if result:
                return success(None, f"成功删除{len(product_ids)}个商品")
            else:
                return error("批量删除商品失败")
        except Exception as e:
            print(f"批量删除商品失败: {str(e)}")
            return error("批量删除商品失败")
    
    def get_product_reviews(self, product_id: int, page: int = 1, limit: int = 10) -> Dict:
        """获取商品评价列表"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 查询评价总数
                    count_sql = """
                        SELECT COUNT(*) as total 
                        FROM py_order_item oi
                        INNER JOIN py_order o ON oi.orderId = o.id
                        INNER JOIN py_user u ON o.userId = u.id
                        WHERE oi.productId = %s AND oi.reviewContent IS NOT NULL
                    """
                    print(f"执行SQL: {count_sql}, 参数: {product_id}")
                    cursor.execute(count_sql, (product_id,))
                    total = cursor.fetchone()['total']
                    
                    # 查询评价数据
                    offset = (page - 1) * limit
                    data_sql = """
                        SELECT oi.id, oi.productName, oi.skuName, oi.productImage,
                               oi.reviewContent, oi.reviewRating, oi.reviewTime,
                               u.username, u.phone
                        FROM py_order_item oi
                        INNER JOIN py_order o ON oi.orderId = o.id
                        INNER JOIN py_user u ON o.userId = u.id
                        WHERE oi.productId = %s AND oi.reviewContent IS NOT NULL
                        ORDER BY oi.reviewTime DESC
                        LIMIT %s OFFSET %s
                    """
                    print(f"执行SQL: {data_sql}, 参数: {product_id, limit, offset}")
                    cursor.execute(data_sql, (product_id, limit, offset))
                    reviews = cursor.fetchall()
                    
                    # 格式化评价数据
                    formatted_reviews = []
                    for review in reviews:
                        # 处理时间格式
                        review_time = review['reviewTime']
                        if review_time and hasattr(review_time, 'strftime'):
                            review_time = review_time.strftime('%Y-%m-%d %H:%M:%S')
                        elif review_time:
                            review_time = str(review_time)
                        else:
                            review_time = ''
                        
                        formatted_reviews.append({
                            'id': review['id'],
                            'productName': review['productName'],
                            'skuName': review['skuName'],
                            'productImage': review['productImage'],
                            'reviewContent': review['reviewContent'],
                            'reviewRating': review['reviewRating'],
                            'reviewTime': review_time,
                            'username': review['username'],
                            'phone': review['phone']
                        })
                    
                    return page_response(formatted_reviews, total, page, limit)
        except Exception as e:
            print(f"获取商品评价失败: {str(e)}")
            return error("获取商品评价失败")
    
    def get_product_review_stats(self, product_id: int) -> Dict:
        """获取商品评价统计信息"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 查询评价统计
                    stats_sql = """
                        SELECT 
                            COUNT(*) as totalReviews,
                            AVG(reviewRating) as averageRating,
                            COUNT(CASE WHEN reviewRating = 5 THEN 1 END) as fiveStarCount,
                            COUNT(CASE WHEN reviewRating = 4 THEN 1 END) as fourStarCount,
                            COUNT(CASE WHEN reviewRating = 3 THEN 1 END) as threeStarCount,
                            COUNT(CASE WHEN reviewRating = 2 THEN 1 END) as twoStarCount,
                            COUNT(CASE WHEN reviewRating = 1 THEN 1 END) as oneStarCount
                        FROM py_order_item 
                        WHERE productId = %s AND reviewContent IS NOT NULL
                    """
                    print(f"执行SQL: {stats_sql}, 参数: {product_id}")
                    cursor.execute(stats_sql, (product_id,))
                    stats = cursor.fetchone()
                    
                    if stats:
                        # 计算平均评分
                        avg_rating = float(stats['averageRating']) if stats['averageRating'] else 0
                        
                        # 计算各星级占比
                        total_reviews = stats['totalReviews']
                        rating_distribution = {
                            'five': round((stats['fiveStarCount'] / total_reviews * 100) if total_reviews > 0 else 0, 1),
                            'four': round((stats['fourStarCount'] / total_reviews * 100) if total_reviews > 0 else 0, 1),
                            'three': round((stats['threeStarCount'] / total_reviews * 100) if total_reviews > 0 else 0, 1),
                            'two': round((stats['twoStarCount'] / total_reviews * 100) if total_reviews > 0 else 0, 1),
                            'one': round((stats['oneStarCount'] / total_reviews * 100) if total_reviews > 0 else 0, 1)
                        }
                        
                        return success({
                            'totalReviews': total_reviews,
                            'averageRating': round(avg_rating, 1),
                            'ratingDistribution': rating_distribution
                        })
                    else:
                        return success({
                            'totalReviews': 0,
                            'averageRating': 0,
                            'ratingDistribution': {
                                'five': 0, 'four': 0, 'three': 0, 'two': 0, 'one': 0
                            }
                        })
        except Exception as e:
            print(f"获取商品评价统计失败: {str(e)}")
            return error("获取商品评价统计失败")

    def get_related_recommendations(self, product_id: int, limit: int = 6) -> Dict[str, Any]:
        """获取关联商品推荐"""
        try:
            self._ensure_db()
            product = self.product_model.get_product_by_id(product_id)
            if not product:
                return error("商品不存在")

            association_rows = self._query_association_rows(product_id, limit)
            recommendations = self._format_recommendations(product, association_rows)
            if not recommendations:
                fallback_rows = self._query_fallback_products(product, product_id, limit)
                recommendations = self._format_fallback_recommendations(product, fallback_rows)

            return success({
                'productId': product_id,
                'recommendations': recommendations,
                'bundleStrategies': self._build_bundle_strategies(product, recommendations)
            })
        except ValueError as exc:
            return error(str(exc))
        except Exception as exc:
            print(f"获取关联商品推荐失败: {str(exc)}")
            return error("获取关联商品推荐失败")

    def _query_association_rows(self, product_id: int, limit: int) -> List[Dict[str, Any]]:
        """查询订单共现商品"""
        placeholders = ', '.join(['%s'] * len(self.VALID_ORDER_STATUS))
        sql = f"""
            SELECT
                p.id, p.name, p.mainImage, p.price, p.originalPrice, p.stock, p.sales,
                p.categoryId, c.name AS categoryName,
                pair_stats.pairCount, target_stats.targetOrderCount,
                related_stats.relatedOrderCount, total_stats.totalOrderCount
            FROM (
                SELECT
                    CASE WHEN oi1.productId = %s THEN oi2.productId ELSE oi1.productId END AS relatedProductId,
                    COUNT(DISTINCT oi1.orderId) AS pairCount
                FROM py_order_item oi1
                JOIN py_order_item oi2 ON oi1.orderId = oi2.orderId AND oi1.productId <> oi2.productId
                JOIN py_order o ON oi1.orderId = o.id
                WHERE (oi1.productId = %s OR oi2.productId = %s)
                  AND o.status IN ({placeholders})
                GROUP BY relatedProductId
            ) pair_stats
            JOIN py_product p ON pair_stats.relatedProductId = p.id AND p.status = 1
            LEFT JOIN py_category c ON p.categoryId = c.id
            CROSS JOIN (
                SELECT COUNT(DISTINCT orderId) AS targetOrderCount
                FROM py_order_item
                WHERE productId = %s
            ) target_stats
            JOIN (
                SELECT productId, COUNT(DISTINCT orderId) AS relatedOrderCount
                FROM py_order_item
                GROUP BY productId
            ) related_stats ON related_stats.productId = p.id
            CROSS JOIN (
                SELECT COUNT(*) AS totalOrderCount
                FROM py_order
                WHERE status IN ({placeholders})
            ) total_stats
            ORDER BY pair_stats.pairCount DESC, p.sales DESC
            LIMIT %s
        """
        params = [product_id, product_id, product_id] + list(self.VALID_ORDER_STATUS)
        params += [product_id] + list(self.VALID_ORDER_STATUS) + [limit]
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()

    def _query_fallback_products(
        self,
        product: Dict[str, Any],
        product_id: int,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """查询同品类热销兜底推荐"""
        sql = """
            SELECT p.id, p.name, p.mainImage, p.price, p.originalPrice, p.stock,
                   p.sales, p.categoryId, c.name AS categoryName
            FROM py_product p
            LEFT JOIN py_category c ON p.categoryId = c.id
            WHERE p.status = 1 AND p.id <> %s AND p.categoryId = %s
            ORDER BY p.sales DESC, p.isHot DESC, p.createTime DESC
            LIMIT %s
        """
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (product_id, product.get('categoryId'), limit))
                return cursor.fetchall()

    def _format_recommendations(
        self,
        product: Dict[str, Any],
        rows: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """格式化关联推荐"""
        result: List[Dict[str, Any]] = []
        for row in rows:
            total_orders = max(int(row.get('totalOrderCount') or 0), 1)
            target_orders = max(int(row.get('targetOrderCount') or 0), 1)
            related_orders = max(int(row.get('relatedOrderCount') or 0), 1)
            confidence = float(row['pairCount']) / target_orders
            support = float(row['pairCount']) / total_orders
            lift = confidence / (related_orders / total_orders)
            item = self._format_product_item(row)
            item.update({
                'reason': '经常一起购买',
                'pairCount': int(row['pairCount']),
                'support': round(support, 4),
                'confidence': round(confidence, 4),
                'lift': round(lift, 4),
                'bundleStrategy': self._build_bundle_strategy(product, item, confidence, lift)
            })
            result.append(item)
        return result

    def _format_fallback_recommendations(
        self,
        product: Dict[str, Any],
        rows: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """格式化兜底推荐"""
        result: List[Dict[str, Any]] = []
        for row in rows:
            item = self._format_product_item(row)
            item.update({
                'reason': '同品类热销',
                'pairCount': 0,
                'support': 0,
                'confidence': 0,
                'lift': 0,
                'bundleStrategy': self._build_bundle_strategy(product, item, 0.0, 0.0)
            })
            result.append(item)
        return result

    def _format_product_item(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """格式化商品信息"""
        return {
            'id': int(row['id']),
            'name': row['name'],
            'mainImage': row.get('mainImage') or '/static/picture/noimg.jpg',
            'price': float(row['price']) if row.get('price') is not None else 0.0,
            'originalPrice': float(row['originalPrice']) if row.get('originalPrice') else None,
            'stock': int(row.get('stock') or 0),
            'sales': int(row.get('sales') or 0),
            'categoryId': int(row['categoryId']) if row.get('categoryId') else None,
            'categoryName': row.get('categoryName') or '未分类',
            'hasDiscount': bool(row.get('hasDiscount')),
            'discountRate': float(row['discountRate']) if row.get('discountRate') is not None else None
        }

    def _build_bundle_strategies(
        self,
        product: Dict[str, Any],
        recommendations: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """生成捆绑销售策略"""
        return [
            item['bundleStrategy']
            for item in recommendations[:3]
            if item.get('bundleStrategy')
        ]

    def _build_bundle_strategy(
        self,
        product: Dict[str, Any],
        item: Dict[str, Any],
        confidence: float,
        lift: float,
    ) -> Dict[str, Any]:
        """生成单个组合购策略"""
        product_price = float(product.get('price') or 0)
        bundle_price = product_price + float(item['price'])
        discount_rate = self._get_bundle_discount_rate(confidence, lift)
        discount_amount = round(bundle_price * discount_rate, 2)
        return {
            'mainProductId': int(product['id']),
            'relatedProductId': int(item['id']),
            'title': f"{product['name']} + {item['name']} 组合购",
            'originalAmount': round(bundle_price, 2),
            'suggestedAmount': round(bundle_price - discount_amount, 2),
            'discountAmount': discount_amount,
            'discountRate': round(discount_rate, 2)
        }

    def _get_bundle_discount_rate(self, confidence: float, lift: float) -> float:
        """计算组合购建议折扣"""
        if confidence >= 0.35 and lift >= 1.2:
            return 0.08
        if confidence >= 0.2 or lift >= 1.1:
            return 0.05
        return 0.03
