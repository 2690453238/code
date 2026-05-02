"""智能选品服务 - 辅助社区团长进行采购决策"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from utils.db_utils import get_db_connection
from utils.response import error, success


class SmartSelectionService:
    """智能选品服务"""

    # 库存风险阈值
    SLOW_DAYS_HIGH = 60
    SLOW_DAYS_MEDIUM = 30
    TURNOVER_DAYS_HIGH = 90
    TURNOVER_DAYS_MEDIUM = 45

    # 补货优先级阈值
    RESTOCK_URGENT_DAYS = 3
    RESTOCK_HIGH_DAYS = 7
    RESTOCK_NORMAL_DAYS = 14

    def get_dashboard(self, supplier_id: Optional[int]) -> Dict[str, Any]:
        """选品总览看板"""
        try:
            new_count = self._count_new_product_candidates(supplier_id)
            slow_moving = self._query_slow_moving(supplier_id)
            slow_high = sum(1 for p in slow_moving if p.get("riskLevel") == "high")
            slow_medium = sum(1 for p in slow_moving if p.get("riskLevel") == "medium")
            urgent = self._count_urgent_restock(supplier_id)
            seasonal = self._count_seasonal_candidates(supplier_id)
            health = self._compute_inventory_health(supplier_id)
            return success({
                "newProductCount": new_count,
                "slowMovingCount": len(slow_moving),
                "slowHighCount": slow_high,
                "slowMediumCount": slow_medium,
                "urgentRestockCount": urgent,
                "seasonalCount": seasonal,
                "inventoryHealth": health,
            })
        except Exception as exc:
            return error(f"获取选品看板失败: {str(exc)}")

    def get_new_products(
        self, supplier_id: Optional[int], limit: int = 50
    ) -> Dict[str, Any]:
        """新品推荐：平台上该团长未上架的热门商品"""
        try:
            products = self._query_new_product_candidates(supplier_id, limit)
            return success({"products": products, "total": len(products)})
        except Exception as exc:
            return error(f"获取新品推荐失败: {str(exc)}")

    def get_slow_moving(
        self, supplier_id: Optional[int], days: int = 90
    ) -> Dict[str, Any]:
        """滞销预警：团长现有商品中表现不佳的"""
        try:
            products = self._query_slow_moving(supplier_id, days)
            return success({"products": products, "total": len(products)})
        except Exception as exc:
            return error(f"获取滞销预警失败: {str(exc)}")

    def get_restock_priority(
        self, supplier_id: Optional[int], forecast_days: int = 7
    ) -> Dict[str, Any]:
        """补货优先级排序"""
        try:
            products = self._query_restock_priorities(supplier_id, forecast_days)
            return success({"products": products, "total": len(products)})
        except Exception as exc:
            return error(f"获取补货优先级失败: {str(exc)}")

    def get_seasonal(
        self, supplier_id: Optional[int], limit: int = 20
    ) -> Dict[str, Any]:
        """季节性选品推荐"""
        try:
            products = self._query_seasonal_products(supplier_id, limit)
            return success({"products": products, "total": len(products)})
        except Exception as exc:
            return error(f"获取季节性选品失败: {str(exc)}")

    # ── 新品推荐 ──────────────────────────────────────────

    def _build_new_product_score(self, row: Dict[str, Any]) -> float:
        """计算新品推荐综合分数"""
        sales = float(row.get("sales") or 0)
        browse_count = float(row.get("browse_count") or 0)
        is_hot = 10 if row.get("isHot") else 0
        is_new = 5 if row.get("isNew") else 0
        price = float(row.get("price") or 0)
        price_penalty = min(price / 100, 20)
        return sales * 0.4 + browse_count * 0.3 + is_hot + is_new - price_penalty

    def _build_reason(
        self, row: Dict[str, Any], score: float, forecast_qty: int = 0
    ) -> str:
        """生成推荐理由"""
        parts = []
        if float(row.get("sales") or 0) > 100:
            parts.append("全平台热销")
        if float(row.get("browse_count") or 0) > 20:
            parts.append("近期浏览热度高")
        if row.get("isHot"):
            parts.append("平台热推")
        if row.get("isNew"):
            parts.append("新品上架")
        if forecast_qty > 50:
            parts.append("预测销量高")
        if not parts:
            if score > 50:
                parts.append("综合推荐")
            else:
                parts.append("同类商品推荐")
        return "、".join(parts[:3])

    def _count_new_product_candidates(self, supplier_id: Optional[int]) -> int:
        """统计可推荐的新品数量"""
        scope_sql, params = self._build_not_my_products_condition(supplier_id)
        month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        sql = f"""
            SELECT COUNT(DISTINCT p.id) AS cnt
            FROM py_product p
            LEFT JOIN py_category c ON p.categoryId = c.id
            {scope_sql}
              AND p.status = 1
              AND (c.status = 1 OR c.status IS NULL)
        """
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                row = cursor.fetchone()
        return row["cnt"] if row else 0

    def _query_new_product_candidates(
        self, supplier_id: Optional[int], limit: int
    ) -> List[Dict[str, Any]]:
        """查询新品推荐候选列表（结合销量预测模型）"""
        fetch_limit = max(limit * 3, 150)
        scope_sql, params = self._build_not_my_products_condition(supplier_id)
        month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

        sql = f"""
            SELECT
                p.id, p.name, p.mainImage, p.price, p.originalPrice,
                p.sales, p.stock, p.isHot, p.isNew, p.supplierId,
                c.id AS categoryId, c.name AS categoryName,
                COALESCE(b.browse_count, 0) AS browse_count
            FROM py_product p
            LEFT JOIN py_category c ON p.categoryId = c.id
            LEFT JOIN (
                SELECT item_id, COUNT(*) AS browse_count
                FROM py_user_browse_history
                WHERE behavior_type = 1
                  AND createtime >= %s
                GROUP BY item_id
            ) b ON b.item_id = CAST(p.id AS CHAR)
            {scope_sql}
              AND p.status = 1
              AND (c.status = 1 OR c.status IS NULL)
            ORDER BY p.sales DESC, p.isHot DESC, p.createTime DESC
            LIMIT %s
        """
        params.insert(0, month_ago)
        params.append(fetch_limit)

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()

        # 集成销量预测模型数据
        forecast_map = {}
        try:
            from service.sales_forecast_service import get_forecast_service
            forecast_result = get_forecast_service().batch_predict(
                supplier_id=None, forecast_days=7
            )
            if forecast_result.get("code") == 200:
                for p in forecast_result["data"]["productPredictions"]:
                    forecast_map[p["productId"]] = p["forecastQuantity"]
        except Exception:
            pass

        results = []
        for row in rows:
            product_id = int(row["id"])
            forecast_qty = forecast_map.get(product_id, 0)

            score = self._build_new_product_score(row)
            if forecast_qty > 0:
                score += min(forecast_qty / 10, 15)

            reason = self._build_reason(row, score, forecast_qty)

            # 推荐购入量：有预测数据则取预测值+20%安全库存，无预测数据则不推荐
            price_val = float(row["price"])
            recommended_qty = int(forecast_qty * 1.2) if forecast_qty > 0 else 0

            results.append({
                "productId": product_id,
                "productName": row["name"],
                "mainImage": row.get("mainImage") or "/static/picture/noimg.jpg",
                "price": price_val,
                "originalPrice": float(row["originalPrice"]) if row.get("originalPrice") else None,
                "sales": int(row["sales"] or 0),
                "stock": int(row["stock"] or 0),
                "isHot": bool(row["isHot"]),
                "isNew": bool(row["isNew"]),
                "categoryId": int(row["categoryId"]) if row.get("categoryId") else None,
                "categoryName": row.get("categoryName") or "未分类",
                "browseCount": int(row["browse_count"] or 0),
                "score": round(score, 2),
                "reason": reason,
                "forecastQuantity": forecast_qty,
                "recommendedQuantity": recommended_qty,
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def _build_not_my_products_condition(
        self, supplier_id: Optional[int]
    ) -> Tuple[str, List[Any]]:
        """构建排除团长已上架商品的条件"""
        if supplier_id is None:
            return "WHERE 1=1", []
        # 找出团长已上架的商品ID列表，排除它们
        return """
            WHERE p.id NOT IN (
                SELECT id FROM py_product
                WHERE supplierId = %s AND status = 1
            )
        """, [supplier_id]

    # ── 滞销预警 ──────────────────────────────────────────

    def _compute_risk_level(
        self, turnover_days: float, slow_days: float
    ) -> Tuple[str, str]:
        """计算风险等级和标签类型"""
        if turnover_days > self.TURNOVER_DAYS_HIGH or slow_days > self.SLOW_DAYS_HIGH:
            return "high", "danger"
        if turnover_days > self.TURNOVER_DAYS_MEDIUM or slow_days > self.SLOW_DAYS_MEDIUM:
            return "medium", "warning"
        return "low", "success"

    def _get_suggestion(self, risk_level: str, turnover_days: float) -> str:
        """根据风险等级生成处理建议"""
        if risk_level == "high":
            if turnover_days > 90:
                return "建议立即促销清仓或下架"
            return "建议降价促销，加快周转"
        if risk_level == "medium":
            return "建议适当降价或捆绑销售"
        return "正常，持续观察"

    def _query_slow_moving(
        self, supplier_id: Optional[int], days: int = 90
    ) -> List[Dict[str, Any]]:
        """查询滞销商品"""
        now = datetime.now()
        month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

        scope_sql = ""
        params: List[Any] = []
        if supplier_id is not None:
            scope_sql = "AND p.supplierId = %s"
            params.append(supplier_id)

        sql = f"""
            SELECT
                p.id, p.name, p.mainImage, p.price, p.stock, p.sales,
                c.name AS categoryName,
                COALESCE(ds.daily_sales, 0) AS daily_avg_sales,
                ds.last_sale_date
            FROM py_product p
            LEFT JOIN py_category c ON p.categoryId = c.id
            LEFT JOIN (
                SELECT
                    oi.productId,
                    SUM(oi.quantity) / 30.0 AS daily_sales,
                    MAX(DATE(STR_TO_DATE(o.createTime, '%%Y-%%m-%%d %%H:%%i:%%s'))) AS last_sale_date
                FROM py_order_item oi
                JOIN py_order o ON oi.orderId = o.id
                WHERE o.status IN ('paid', 'shipped', 'delivered', 'completed')
                  AND STR_TO_DATE(o.createTime, '%%Y-%%m-%%d %%H:%%i:%%s') >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                GROUP BY oi.productId
            ) ds ON ds.productId = p.id
            WHERE p.status = 1
              {scope_sql}
            ORDER BY p.stock DESC
        """
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()

        results = []
        for row in rows:
            stock = float(row["stock"] or 0)
            daily_avg = float(row["daily_avg_sales"] or 0)
            turnover_days = stock / max(daily_avg, 0.1) if daily_avg > 0 else 999

            last_sale = row.get("last_sale_date")
            slow_days = 999
            if last_sale:
                try:
                    last_date = datetime.strptime(str(last_sale), "%Y-%m-%d")
                    slow_days = (now - last_date).days
                except (ValueError, TypeError):
                    slow_days = 999
            elif daily_avg > 0:
                pass
            else:
                slow_days = 999

            risk_level, tag_type = self._compute_risk_level(turnover_days, slow_days)
            suggestion = self._get_suggestion(risk_level, turnover_days)

            results.append({
                "productId": int(row["id"]),
                "productName": row["name"],
                "mainImage": row.get("mainImage") or "/static/picture/noimg.jpg",
                "price": float(row["price"]),
                "stock": int(stock),
                "sales": int(row["sales"] or 0),
                "categoryName": row.get("categoryName") or "未分类",
                "dailyAvgSales": round(daily_avg, 2),
                "turnoverDays": round(turnover_days, 1) if turnover_days < 999 else None,
                "slowDays": slow_days if slow_days < 999 else None,
                "riskLevel": risk_level,
                "tagType": tag_type,
                "suggestion": suggestion,
            })

        results.sort(
            key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["riskLevel"]]
        )
        return results

    # ── 补货优先级 ────────────────────────────────────────

    def _count_urgent_restock(self, supplier_id: Optional[int]) -> int:
        """统计紧急补货商品数"""
        products = self._query_restock_priorities(supplier_id)
        return sum(1 for p in products if p.get("priorityLevel") == 1)

    def _query_restock_priorities(
        self, supplier_id: Optional[int], forecast_days: int = 7
    ) -> List[Dict[str, Any]]:
        """查询补货优先级"""
        now = datetime.now()
        month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

        scope_sql = ""
        params: List[Any] = []
        if supplier_id is not None:
            scope_sql = "AND p.supplierId = %s"
            params.append(supplier_id)

        sql = f"""
            SELECT
                p.id, p.name, p.mainImage, p.price, p.stock, p.sales,
                c.name AS categoryName,
                COALESCE(ds.daily_sales, 0) AS daily_avg_sales,
                COALESCE(ds.week_sales, 0) AS week_sales
            FROM py_product p
            LEFT JOIN py_category c ON p.categoryId = c.id
            LEFT JOIN (
                SELECT
                    oi.productId,
                    SUM(oi.quantity) / 30.0 AS daily_sales,
                    SUM(CASE
                        WHEN STR_TO_DATE(o.createTime, '%%Y-%%m-%%d %%H:%%i:%%s')
                             >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                        THEN oi.quantity ELSE 0
                    END) AS week_sales
                FROM py_order_item oi
                JOIN py_order o ON oi.orderId = o.id
                WHERE o.status IN ('paid', 'shipped', 'delivered', 'completed')
                GROUP BY oi.productId
            ) ds ON ds.productId = p.id
            WHERE p.status = 1
              {scope_sql}
            ORDER BY p.sales DESC
        """
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()

        results = []
        for row in rows:
            stock = float(row["stock"] or 0)
            daily_avg = float(row["daily_avg_sales"] or 0)
            week_sales = float(row["week_sales"] or 0)
            sellable_days = stock / max(daily_avg, 0.1) if daily_avg > 0 else 999

            priority_level, priority_label = self._compute_priority(
                sellable_days, week_sales, daily_avg
            )
            suggested_restock = self._calc_suggested_restock(
                daily_avg, stock, forecast_days
            )

            results.append({
                "productId": int(row["id"]),
                "productName": row["name"],
                "mainImage": row.get("mainImage") or "/static/picture/noimg.jpg",
                "price": float(row["price"]),
                "stock": int(stock),
                "sales": int(row["sales"] or 0),
                "categoryName": row.get("categoryName") or "未分类",
                "dailyAvgSales": round(daily_avg, 2),
                "weekSales": int(week_sales),
                "sellableDays": round(sellable_days, 1) if sellable_days < 999 else None,
                "priorityLevel": priority_level,
                "priorityLabel": priority_label,
                "suggestedRestock": suggested_restock,
            })

        results.sort(key=lambda x: x["priorityLevel"])
        return results

    def _compute_priority(
        self, sellable_days: float, week_sales: float, daily_avg: float
    ) -> Tuple[int, str]:
        """计算补货优先级"""
        if sellable_days < self.RESTOCK_URGENT_DAYS and week_sales > 0:
            return 1, "紧急"
        if sellable_days < self.RESTOCK_HIGH_DAYS and daily_avg > 0:
            return 2, "较高"
        if sellable_days < self.RESTOCK_NORMAL_DAYS:
            return 3, "一般"
        return 4, "暂不需补货"

    def _calc_suggested_restock(
        self, daily_avg: float, stock: float, forecast_days: int
    ) -> int:
        """计算建议补货量"""
        if daily_avg <= 0:
            return 0
        target = daily_avg * forecast_days * 1.2  # 预留20%安全库存
        gap = int(target - stock)
        return max(gap, 0)

    # ── 季节性推荐 ────────────────────────────────────────

    def _count_seasonal_candidates(self, supplier_id: Optional[int]) -> int:
        """统计季节选品推荐数量"""
        products = self._query_seasonal_products(supplier_id)
        return len(products)

    def _query_seasonal_products(
        self, supplier_id: Optional[int], limit: int = 20
    ) -> List[Dict[str, Any]]:
        """查询季节性推荐商品"""
        current_month = datetime.now().month

        exclusion_sql = ""
        params: List[Any] = [current_month]
        if supplier_id is not None:
            exclusion_sql = (
                "AND p.id NOT IN ("
                "  SELECT id FROM py_product"
                "  WHERE supplierId = %s AND status = 1"
                ")"
            )
            params.append(supplier_id)

        sql = f"""
            SELECT
                p.id, p.name, p.mainImage, p.price, p.originalPrice,
                p.sales, p.stock, p.isHot, p.isNew,
                c.id AS categoryId, c.name AS categoryName,
                COALESCE(seasonal.total_qty, 0) AS season_sales,
                COALESCE(seasonal.order_cnt, 0) AS season_orders
            FROM py_product p
            LEFT JOIN py_category c ON p.categoryId = c.id
            LEFT JOIN (
                SELECT
                    oi.productId,
                    SUM(oi.quantity) AS total_qty,
                    COUNT(DISTINCT oi.orderId) AS order_cnt
                FROM py_order_item oi
                JOIN py_order o ON oi.orderId = o.id
                WHERE o.status IN ('paid', 'shipped', 'delivered', 'completed')
                  AND MONTH(STR_TO_DATE(o.createTime, '%%Y-%%m-%%d %%H:%%i:%%s')) = %s
                GROUP BY oi.productId
            ) seasonal ON seasonal.productId = p.id
            WHERE p.status = 1
              AND (c.status = 1 OR c.status IS NULL)
              AND COALESCE(seasonal.total_qty, 0) > 0
              {exclusion_sql}
            ORDER BY seasonal.total_qty DESC, p.sales DESC
            LIMIT %s
        """
        params.append(limit)

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()

        now = datetime.now()
        month_names = [
            "", "1月", "2月", "3月", "4月", "5月", "6月",
            "7月", "8月", "9月", "10月", "11月", "12月",
        ]
        current_month_name = month_names[current_month]

        results = []
        for row in rows:
            results.append({
                "productId": int(row["id"]),
                "productName": row["name"],
                "mainImage": row.get("mainImage") or "/static/picture/noimg.jpg",
                "price": float(row["price"]),
                "originalPrice": float(row["originalPrice"]) if row.get("originalPrice") else None,
                "sales": int(row["sales"] or 0),
                "stock": int(row["stock"] or 0),
                "isHot": bool(row["isHot"]),
                "isNew": bool(row["isNew"]),
                "categoryId": int(row["categoryId"]) if row.get("categoryId") else None,
                "categoryName": row.get("categoryName") or "未分类",
                "seasonSales": int(row["season_sales"] or 0),
                "seasonOrders": int(row["season_orders"] or 0),
                "seasonLabel": f"{current_month_name}应季推荐",
            })
        return results

    # ── 批量采购 ──────────────────────────────────────────

    def batch_purchase(
        self, supplier_id: int, products: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """批量采购：将推荐商品复制到团长自己的商品列表，支持自定义采购数量"""
        if not products:
            return error("请选择要采购的商品")

        product_ids = [p["productId"] for p in products]
        quantity_map = {p["productId"]: max(int(p.get("quantity", 10)), 1) for p in products}

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                placeholders = ",".join(["%s"] * len(product_ids))
                cursor.execute(
                    f"SELECT * FROM py_product WHERE id IN ({placeholders}) AND status = 1",
                    product_ids,
                )
                source_products = cursor.fetchall()

                if not source_products:
                    return error("未找到指定的商品")

                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_ids = []

                for prod in source_products:
                    cursor.execute(
                        "SELECT id FROM py_product WHERE supplierId = %s AND name = %s AND status = 1",
                        (supplier_id, prod["name"]),
                    )
                    if cursor.fetchone():
                        continue

                    purchase_qty = quantity_map.get(int(prod["id"]), 10)

                    cursor.execute(
                        """INSERT INTO py_product
                        (supplierId, name, description, categoryId, brand, mainImage, galleryImages,
                         price, originalPrice, stock, sales, status, isHot, isNew, createTime, updateTime)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, 1, 0, 0, %s, %s)""",
                        (
                            supplier_id,
                            prod["name"],
                            prod["description"],
                            prod["categoryId"],
                            prod["brand"],
                            prod["mainImage"],
                            prod.get("galleryImages"),
                            prod["price"],
                            prod.get("originalPrice"),
                            purchase_qty,
                            now,
                            now,
                        ),
                    )
                    new_ids.append(cursor.lastrowid)

                conn.commit()

        return success({
            "purchasedCount": len(new_ids),
            "newProductIds": new_ids,
        })

    # ── 库存健康度 ─────────────────────────────────────────

    def _compute_inventory_health(
        self, supplier_id: Optional[int]
    ) -> Dict[str, Any]:
        """计算库存健康度分布"""
        slow = self._query_slow_moving(supplier_id)
        restock = self._query_restock_priorities(supplier_id)

        total_on_shelf = 0
        if supplier_id is not None:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT COUNT(*) AS cnt FROM py_product WHERE supplierId = %s AND status = 1",
                        (supplier_id,),
                    )
                    total_on_shelf = cursor.fetchone()["cnt"] or 0

        overstocked = sum(1 for p in slow if p.get("riskLevel") == "high")
        normal = max(0, total_on_shelf - overstocked - len(restock))
        return {
            "totalOnShelf": total_on_shelf,
            "healthy": normal,
            "overstocked": overstocked,
            "understocked": sum(1 for p in restock if p.get("priorityLevel", 99) <= 2),
        }
