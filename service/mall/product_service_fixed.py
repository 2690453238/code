from typing import Any, Dict, List, Optional

from service.mall.product_service import ProductService as BaseProductService


class ProductService(BaseProductService):
    """修正版商品服务：按社区团长账号隔离商品数据"""

    GLOBAL_ROLES = {'system_admin', 'platform_operator'}

    def _get_supplier_scope_id(self, user_info: Optional[Dict]) -> Optional[int]:
        if not user_info:
            return None
        if user_info.get('role') in self.GLOBAL_ROLES:
            return None
        if user_info.get('role') == 'community_leader':
            return user_info.get('id')
        if user_info.get('role') == 'user':
            user_id = user_info.get('id')
            if not user_id:
                return None
            from utils.db_utils import execute_query
            leaders = execute_query("""
                SELECT cl.id FROM py_user u
                JOIN py_community c ON u.supplierCode = c.communityCode
                JOIN py_user cl ON c.leaderUserId = cl.id
                WHERE u.id = %s AND u.role = 'user' AND cl.role = 'community_leader'
            """, (user_id,))
            return leaders[0]['id'] if leaders else None
        return None

    def get_products(
        self,
        category_id: int = None,
        status: int = None,
        page: int = 1,
        limit: int = 10,
        keyword: str = None,
        sort_type: str = 'default',
        user_info: Optional[Dict] = None
    ) -> Dict:
        supplier_id = self._get_supplier_scope_id(user_info)
        return super().get_products(category_id, status, page, limit, keyword, sort_type) \
            if supplier_id is None else self._get_products_scoped(category_id, status, page, limit, keyword, sort_type, supplier_id)

    def _get_products_scoped(self, category_id, status, page, limit, keyword, sort_type, supplier_id):
        result = self.product_model.get_products(category_id, status, page, limit, keyword, sort_type, supplier_id)
        from utils.response import page_response
        return page_response(result['rows'], result['total'], result['page'], result['limit'])

    def get_hot_products(self, limit: int = 10, user_info: Optional[Dict] = None) -> Dict:
        supplier_id = self._get_supplier_scope_id(user_info)
        return super().get_hot_products(limit) \
            if supplier_id is None else self._get_hot_scoped(limit, supplier_id)

    def _get_hot_scoped(self, limit: int, supplier_id: int) -> Dict:
        result = self.product_model.get_products(status=1, limit=limit, supplier_id=supplier_id)
        hot_products = [p for p in result['rows'] if p.get('isHot') == 1]
        from utils.response import success
        return success(hot_products)

    def get_new_products(self, limit: int = 10, user_info: Optional[Dict] = None) -> Dict:
        supplier_id = self._get_supplier_scope_id(user_info)
        return super().get_new_products(limit) \
            if supplier_id is None else self._get_new_scoped(limit, supplier_id)

    def _get_new_scoped(self, limit: int, supplier_id: int) -> Dict:
        result = self.product_model.get_products(status=1, limit=limit, supplier_id=supplier_id)
        new_products = [p for p in result['rows'] if p.get('isNew') == 1]
        from utils.response import success
        return success(new_products)

    def get_related_recommendations(
        self, product_id: int, limit: int = 6,
        user_info: Optional[Dict] = None
    ) -> Dict:
        supplier_id = self._get_supplier_scope_id(user_info)
        return super().get_related_recommendations(product_id, limit) \
            if supplier_id is None else self._get_recommendations_scoped(product_id, limit, supplier_id)

    def _get_recommendations_scoped(self, product_id: int, limit: int, supplier_id: int) -> Dict:
        from utils.db_utils import get_db_connection
        from utils.response import success, error
        from model.mall.product_model import ProductModel

        with get_db_connection() as conn:
            product_model = ProductModel(conn)
            product = product_model.get_product_by_id(product_id)
        if not product:
            return error("商品不存在")

        association_rows = self._query_association_rows_scoped(product_id, limit, supplier_id)
        recommendations = self._format_recommendations(product, association_rows)
        if not recommendations:
            fallback_rows = self._query_fallback_products_scoped(product, product_id, limit, supplier_id)
            recommendations = self._format_fallback_recommendations(product, fallback_rows)

        return success({
            'productId': product_id,
            'recommendations': recommendations,
            'bundleStrategies': self._build_bundle_strategies(product, recommendations)
        })

    def _query_association_rows_scoped(
        self, product_id: int, limit: int, supplier_id: int
    ) -> List[Dict[str, Any]]:
        from utils.db_utils import get_db_connection
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
            JOIN py_product p ON pair_stats.relatedProductId = p.id AND p.status = 1 AND p.supplierId = %s
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
        params += [supplier_id, product_id] + list(self.VALID_ORDER_STATUS) + [limit]
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()

    def _query_fallback_products_scoped(
        self, product: Dict[str, Any], product_id: int, limit: int, supplier_id: int
    ) -> List[Dict[str, Any]]:
        from utils.db_utils import get_db_connection
        sql = """
            SELECT p.id, p.name, p.mainImage, p.price, p.originalPrice, p.stock,
                   p.sales, p.categoryId, c.name AS categoryName
            FROM py_product p
            LEFT JOIN py_category c ON p.categoryId = c.id
            WHERE p.status = 1 AND p.id <> %s AND p.categoryId = %s AND p.supplierId = %s
            ORDER BY p.sales DESC, p.isHot DESC, p.createTime DESC
            LIMIT %s
        """
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (product_id, product.get('categoryId'), supplier_id, limit))
                return cursor.fetchall()

    def create_product(self, product_data: Dict, user_info: Optional[Dict] = None) -> Dict:
        supplier_id = self._get_supplier_scope_id(user_info)
        if supplier_id is not None:
            product_data['supplierId'] = supplier_id
        return super().create_product(product_data)

    def update_product(self, product_id: int, product_data: Dict, user_info: Optional[Dict] = None) -> Dict:
        from utils.response import success, error
        try:
            supplier_id = self._get_supplier_scope_id(user_info)
            result = self.product_model.update_product(product_id, product_data, supplier_id)
            if result:
                return success(None, "商品更新成功")
            return error("商品更新失败或无权限")
        except Exception:
            return error("更新商品失败")

    def delete_product(self, product_id: int, user_info: Optional[Dict] = None) -> Dict:
        from utils.response import success, error
        try:
            supplier_id = self._get_supplier_scope_id(user_info)
            result = self.product_model.delete_product(product_id, supplier_id)
            if result:
                return success(None, "商品删除成功")
            return error("商品删除失败或无权限")
        except Exception:
            return error("删除商品失败")

    def update_product_status(self, product_id: int, status: int, user_info: Optional[Dict] = None) -> Dict:
        from utils.response import success, error
        try:
            supplier_id = self._get_supplier_scope_id(user_info)
            result = self.product_model.update_product_status(product_id, status, supplier_id)
            if result:
                status_text = "上架" if status == 1 else "下架"
                return success(None, f"商品{status_text}成功")
            return error("商品状态更新失败或无权限")
        except Exception:
            return error("更新商品状态失败")

    def batch_delete_products(self, product_ids: List[int], user_info: Optional[Dict] = None) -> Dict:
        from utils.response import success, error
        try:
            supplier_id = self._get_supplier_scope_id(user_info)
            result = self.product_model.batch_delete_products(product_ids, supplier_id)
            if result:
                return success(None, f"成功删除{len(product_ids)}个商品")
            return error("批量删除商品失败或无权限")
        except Exception:
            return error("批量删除商品失败")
