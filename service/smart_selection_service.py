"""
智能选品服务 - 辅助社区团长进行采购决策

本服务整合销量预测数据与商品基础信息，为社区团长提供四大核心决策辅助：

  ① 商品推荐（_query_new_product_candidates）
     — 基于 5 维度综合推荐分（0-100 分）排序
     — 维度：预测销量(35分) + 历史销量(20分) + 库存健康(20分)
              + 价格利润(15分) + 热度加分(10分)
     — 推荐分 ≥ 60 的商品在前端自动预勾选

  ② 滞销预警（_query_slow_moving）
     — 通过周转天数与动销天数双维度评估
     — 输出 high / medium / low / normal 四级风险等级
     — 高风险商品建议促销清仓或下架

  ③ 补货优先级（_query_restock_priorities）
     — 根据可售天数（库存 ÷ 日均预测销量）判断紧急程度
     — 输出 紧急 / 较高 / 一般 / 暂不需 四级优先级

  ④ 季节性推荐（_query_seasonal_products）
     — 基于当前月份的历史热销数据推荐应季商品

依赖关系：
  - sales_forecast_service.SalesForecastService — 获取销量预测数据
  - purchase_service.PurchaseService — 一键采购生成订单
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from utils.db_utils import get_db_connection
from utils.response import error, success

from service.purchase_service import PurchaseService

# 销量预测缓存（按 supplier_id 隔离，避免每次请求都重新训练）
_forecast_cache: Dict[str, Dict[str, Any]] = {}


def _get_cached_forecast(supplier_id=None, forecast_days=7) -> Dict[str, Any]:
    """获取缓存的销量预测结果（按 supplier_id 缓存，5分钟过期）"""
    global _forecast_cache
    now = datetime.now().timestamp()
    cache_key = f"s:{supplier_id}_d:{forecast_days}"
    entry = _forecast_cache.get(cache_key)
    if entry and now < entry["expires_at"]:
        return entry["data"]
    try:
        from service.sales_forecast_service import get_forecast_service
        result = get_forecast_service().batch_predict(
            supplier_id=supplier_id, forecast_days=forecast_days
        )
        if result.get("code") == 200:
            _forecast_cache[cache_key] = {"data": result, "expires_at": now + 300}
        return result
    except Exception:
        return {"code": 500, "data": {"productPredictions": []}}


class SmartSelectionService:
    """
    智能选品服务

    为社区团长提供商品推荐、滞销预警、补货优先级、季节性推荐四大功能。
    核心算法是 _compute_recommendation_score 中实现的五维度综合评分模型。
    """

    # ── 库存风险判定阈值 ────────────────────────────────────
    # 动销天数阈值（距离上次销售的天数）
    SLOW_DAYS_HIGH = 60      # 超过60天未动销 → 高风险
    SLOW_DAYS_MEDIUM = 30    # 超过30天未动销 → 中风险
    # 周转天数阈值（库存按日均销量可消耗的天数）
    TURNOVER_DAYS_HIGH = 14  # 可供超过14天 → 库存积压（高风险）
    TURNOVER_DAYS_MEDIUM = 7 # 可供超过7天  → 库存偏多（中风险）
    TURNOVER_DAYS_LOW = 5    # 可供超过5天  → 轻微过剩（低风险）

    # ── 补货优先级阈值 ──────────────────────────────────────
    RESTOCK_URGENT_DAYS = 3   # 可售天数 < 3天 → 紧急补货
    RESTOCK_HIGH_DAYS = 7     # 可售天数 < 7天 → 较高优先级
    RESTOCK_NORMAL_DAYS = 14  # 可售天数 < 14天 → 一般优先级

    def __init__(self):
        pass

    def get_dashboard(self, supplier_id: Optional[int]) -> Dict[str, Any]:
        """选品总览看板"""
        try:
            slow_moving = self._query_slow_moving(supplier_id, limit=200)
            slow_high = sum(1 for p in slow_moving if p.get("riskLevel") == "high")
            slow_medium = sum(1 for p in slow_moving if p.get("riskLevel") == "medium")
            restock = self._query_restock_priorities(supplier_id, limit=200)
            urgent = sum(1 for p in restock if p.get("priorityLevel") == 1)
            seasonal = self._count_seasonal_candidates(supplier_id)
            health = self._compute_inventory_health(
                supplier_id, slow_moving, restock
            )
            # 统计推荐分 >= 60 的商品数（待选商品）
            new_products_result = self.get_new_products(supplier_id, limit=999)
            new_product_count = 0
            if new_products_result.get("code") == 200:
                products = new_products_result["data"]["products"]
                new_product_count = sum(1 for p in products if p.get("recommendationScore", 0) >= 60)
            return success({
                "newProductCount": new_product_count,
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
        """商品推荐：基于销量预测数据排序"""
        try:
            products = self._query_new_product_candidates(supplier_id, limit)
            return success({"products": products, "total": len(products)})
        except Exception as exc:
            return error(f"获取商品推荐失败: {str(exc)}")

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

    # ── 商品推荐（基于销量预测） ──────────────────────────────

    def _compute_recommendation_score(
        self,
        forecast_qty: float,
        sales: int,
        stock: int,
        price: float,
        original_price: Optional[float],
        max_forecast: float,
        max_sales: int,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        计算综合推荐分（0-100分），基于五维度加权评分模型

        评分模型设计思路：
        ─────────────────────────────────────────────────────────
        推荐分 = 预测销量得分(35) + 历史销量得分(20)
               + 库存健康得分(20) + 价格系数得分(15)
               + 热度加分(10)

        各维度设计理由：

        ① 预测销量得分（0-35分）—— 权重最高
           基于机器学习模型的销量预测结果，反映商品未来N天的预期销量。
           采用 Min-Max 归一化（除以最大值）后乘以权重，保证不同量级的
           商品之间分数可比。得分越高，说明该商品未来越有销售潜力。

        ② 历史销量得分（0-20分）
           过去一段时间的实际销量，验证市场认可度。
           同样使用 Min-Max 归一化。一个商品历史表现好，未来大概率
           继续表现好。与预测销量得分形成"历史+未来"的双重验证。

        ③ 库存健康得分（0-20分）
           库存过低（< 10件）无法正常销售，库存过高则占用资金和仓储。
           最优区间设计为 50-200 件（20分满分），过少或过多均减分。
           这是对"可销售性"的评估 —— 只有可正常销售的商品才值得推荐。

        ④ 价格系数得分（0-15分）
           通过（原价-现价）/原价计算利润空间。
           利润空间充足（≥ 30%）→ 15分，团长有更多定价/促销灵活性。
           利润微薄（< 5%）→ 5分，即使销量好也不值得大量采购。

        ⑤ 热度加分（0-10分）
           平台标记的 isHot（热销）加5分，isNew（新品）加5分。
           热销商品说明经过市场验证，新品说明平台正在重点推广。
           这部分由调用方在外部累加（见 _query_new_product_candidates）。
        """
        score = 0.0
        details = {}

        # ① 预测销量得分 (0-35分) — 核心维度，权重最高
        #     使用 Min-Max 归一化：当前值 / 最大值 × 权重
        if max_forecast > 0:
            forecast_score = round(35 * (forecast_qty / max_forecast), 1)
        else:
            forecast_score = 0
        score += forecast_score
        details["forecastScore"] = forecast_score

        # ② 历史销量得分 (0-20分) — 市场验证
        if max_sales > 0:
            sales_score = round(20 * (sales / max_sales), 1)
        else:
            sales_score = 0
        score += sales_score
        details["salesScore"] = sales_score

        # ③ 库存健康得分 (0-20分) — 保证可销售
        #     区间划分：
        #       stock ≤ 0   →  0分（无货可卖）
        #       1 ~ 9       →  5分（严重不足）
        #       10 ~ 49     → 15分（偏少但可用）
        #       50 ~ 199    → 20分（最佳区间）
        #       200 ~ 499   → 15分（偏多）
        #       500 ~ 999   → 10分（积压趋势）
        #       1000+       →  5分（严重积压）
        if stock <= 0:
            stock_score = 0
        elif stock < 10:
            stock_score = 5
        elif stock < 50:
            stock_score = 15
        elif stock < 200:
            stock_score = 20
        elif stock < 500:
            stock_score = 15
        elif stock < 1000:
            stock_score = 10
        else:
            stock_score = 5
        score += stock_score
        details["stockScore"] = stock_score

        # ④ 价格系数得分 (0-15分) — 利润空间
        #     利润空间 = (原价 - 现价) / 原价
        #     利润越高的商品，团长操作空间越大
        if original_price and original_price > 0 and price > 0:
            margin_ratio = (original_price - price) / original_price
            if margin_ratio >= 0.3:
                price_score = 15  # 利润 ≥ 30%
            elif margin_ratio >= 0.15:
                price_score = 12  # 利润 ≥ 15%
            elif margin_ratio >= 0.05:
                price_score = 8   # 利润 ≥ 5%
            else:
                price_score = 5   # 微利或倒挂
        else:
            price_score = 5       # 无法计算利润时给基础分
        score += price_score
        details["priceScore"] = price_score

        # ⑤ 热度加分由调用方在外部累加（isHot +5, isNew +5）
        details["hotScore"] = 0

        score = round(min(score, 100), 1)
        return score, details

    def _query_new_product_candidates(
        self, supplier_id: Optional[int], limit: int
    ) -> List[Dict[str, Any]]:
        """查询商品推荐列表（基于销量预测和综合推荐分排序）"""
        fetch_limit = max(limit * 3, 150)
        scope_sql, params = self._build_community_products_condition(supplier_id)

        sql = f"""
            SELECT
                p.id, p.name, p.mainImage, p.price, p.originalPrice,
                p.sales, p.stock, p.isHot, p.isNew, p.supplierId,
                c.id AS categoryId, c.name AS categoryName
            FROM py_product p
            LEFT JOIN py_category c ON p.categoryId = c.id
            {scope_sql}
              AND p.status = 1
              AND (c.status = 1 OR c.status IS NULL)
            ORDER BY p.sales DESC, p.createTime DESC
            LIMIT %s
        """
        params.append(fetch_limit)

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()

        # 从销量预测获取数据
        forecast_map = {}
        forecast_result = _get_cached_forecast(supplier_id=supplier_id, forecast_days=7)
        if forecast_result.get("code") == 200:
            for p in forecast_result["data"]["productPredictions"]:
                forecast_map[p["productId"]] = p

        # 先组装基础数据
        results = []
        for row in rows:
            product_id = int(row["id"])
            forecast_data = forecast_map.get(product_id)
            if forecast_data:
                forecast_qty = int(forecast_data["forecastQuantity"])
                recommended_qty = forecast_data["purchaseAdvice"]["suggestedQuantity"]
            else:
                forecast_qty = 0
                recommended_qty = 0

            results.append({
                "productId": product_id,
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
                "forecastQuantity": forecast_qty,
                "recommendedQuantity": recommended_qty,
            })

        # 计算各维度最大值用于归一化
        max_forecast = max((r["forecastQuantity"] for r in results), default=0)
        max_sales = max((r["sales"] for r in results), default=0)

        # 为每个商品计算综合推荐分
        for r in results:
            score, details = self._compute_recommendation_score(
                forecast_qty=r["forecastQuantity"],
                sales=r["sales"],
                stock=r["stock"],
                price=r["price"],
                original_price=r["originalPrice"],
                max_forecast=max_forecast,
                max_sales=max_sales,
            )
            # 热度加分
            hot_bonus = 0
            if r["isHot"]:
                hot_bonus += 5
            if r["isNew"]:
                hot_bonus += 5
            details["hotScore"] = hot_bonus
            score = round(min(score + hot_bonus, 100), 1)

            r["recommendationScore"] = score
            r["scoreDetails"] = details

        # 按综合推荐分从高到低排序
        results.sort(key=lambda x: x["recommendationScore"], reverse=True)
        return results[:limit]

    def _build_community_products_condition(
        self, supplier_id: Optional[int]
    ) -> Tuple[str, List[Any]]:
        """构建仅推荐本社区商品的条件"""
        if supplier_id is None:
            return "WHERE 1=1", []
        return "WHERE p.supplierId = %s", [supplier_id]

    # ── 滞销预警 ──────────────────────────────────────────

    def _compute_risk_level(
        self, turnover_days: float, slow_days: float
    ) -> Tuple[str, str]:
        """
        计算滞销风险等级

        双维度评估法：
          ① 周转天数（turnover_days）
             现有库存按日均销量能卖多少天
             计算公式：stock / daily_avg_sales
             如库存100件，日均卖10件，周转天数 = 10天

          ② 动销天数（slow_days）
             距离最近一次销售过去了多少天
             如上次销售在30天前，动销天数 = 30天

        等级判定：
          high   → 周转 > 14天 或 动销 > 60天
                   库存积压严重或长期无人购买，需立即处理
          medium → 周转 > 7天  或 动销 > 30天
                   库存偏多或销售放缓，需关注
          low    → 周转 > 5天
                   轻微过剩，提前关注即可
          normal → 周转 ≤ 5天
                   库存健康，正常销售

        返回值：
          (风险等级, 标签类型) 用于前端渲染不同颜色的标签
          danger=红色, warning=橙色, info=蓝色, success=绿色
        """
        if turnover_days > self.TURNOVER_DAYS_HIGH or slow_days > self.SLOW_DAYS_HIGH:
            return "high", "danger"
        if turnover_days > self.TURNOVER_DAYS_MEDIUM or slow_days > self.SLOW_DAYS_MEDIUM:
            return "medium", "warning"
        if turnover_days > self.TURNOVER_DAYS_LOW:
            return "low", "info"
        return "normal", "success"

    def _get_suggestion(self, risk_level: str, turnover_days: float) -> str:
        """根据风险等级生成可操作的处理建议"""
        if risk_level == "high":
            if turnover_days > 14:
                return "建议立即促销清仓或下架"
            return "建议降价促销，加快周转"
        if risk_level == "medium":
            return "建议适当降价或捆绑销售"
        if risk_level == "low":
            return "建议关注，提前备货"
        return "正常，持续观察"

    def _query_slow_moving(
        self, supplier_id: Optional[int], days: int = 90, limit: int = 0
    ) -> List[Dict[str, Any]]:
        """查询滞销商品"""
        now = datetime.now()
        month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

        scope_sql = ""
        params: List[Any] = []
        if supplier_id is not None:
            scope_sql = "AND p.supplierId = %s"
            params.append(supplier_id)

        limit_sql = ""
        if limit > 0:
            limit_sql = "LIMIT %s"
            params.append(limit)

        sql = f"""
            SELECT
                p.id, p.name, p.mainImage, p.price, p.stock, p.sales,
                c.name AS categoryName,
                COALESCE(ds.daily_sales, 0) AS daily_avg_sales,
                ds.last_sale_date,
                sd.discountRate
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
            LEFT JOIN py_supplier_discount sd ON sd.productId = p.id AND sd.supplierId = p.supplierId
            WHERE p.status = 1
              {scope_sql}
            ORDER BY p.stock DESC
            {limit_sql}
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
                "discountRate": float(row["discountRate"]) if row.get("discountRate") else None,
            })

        results.sort(
            key=lambda x: {"high": 0, "medium": 1, "low": 2, "normal": 3}[x["riskLevel"]]
        )
        return results

    # ── 补货优先级 ────────────────────────────────────────

    def _count_urgent_restock(self, supplier_id: Optional[int]) -> int:
        """统计紧急补货商品数（仅计数，轻量查询）"""
        scope_sql = ""
        params: List[Any] = []
        if supplier_id is not None:
            scope_sql = "AND p.supplierId = %s"
            params.append(supplier_id)
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"""
                        SELECT COUNT(*) AS cnt FROM py_product p
                        WHERE p.status = 1 AND p.stock < 10 {scope_sql}
                    """, params)
                    return cursor.fetchone()["cnt"] or 0
        except Exception:
            return 0

    def _query_restock_priorities(
        self, supplier_id: Optional[int], forecast_days: int = 7, limit: int = 0
    ) -> List[Dict[str, Any]]:
        """查询补货优先级（基于销量预测模型数据，与销量预测界面的采购建议一致）"""
        scope_sql = ""
        params: List[Any] = []
        if supplier_id is not None:
            scope_sql = "AND p.supplierId = %s"
            params.append(supplier_id)

        limit_sql = ""
        if limit > 0:
            limit_sql = "LIMIT %s"
            params.append(limit)

        sql = f"""
            SELECT
                p.id, p.name, p.mainImage, p.price, p.stock, p.sales,
                c.name AS categoryName
            FROM py_product p
            LEFT JOIN py_category c ON p.categoryId = c.id
            WHERE p.status = 1
              {scope_sql}
            ORDER BY p.sales DESC
            {limit_sql}
        """
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()

        # 直接从销量预测获取数据，与销量预测界面的采购建议保持一致
        forecast_map = {}
        forecast_result = _get_cached_forecast(supplier_id=supplier_id, forecast_days=forecast_days)
        if forecast_result.get("code") == 200:
            for p in forecast_result["data"]["productPredictions"]:
                forecast_map[p["productId"]] = p

        results = []
        for row in rows:
            product_id = int(row["id"])
            stock = float(row["stock"] or 0)
            forecast_data = forecast_map.get(product_id)

            if forecast_data:
                forecast_qty = float(forecast_data["forecastQuantity"])
                daily_avg = forecast_qty / forecast_days if forecast_days > 0 else 0
                suggested_restock = forecast_data["purchaseAdvice"]["suggestedQuantity"]
            else:
                forecast_qty = 0
                daily_avg = 0
                suggested_restock = 0

            sellable_days = stock / max(daily_avg, 0.1) if daily_avg > 0 else 999
            priority_level, priority_label = self._compute_priority(
                sellable_days, forecast_qty, daily_avg
            )

            results.append({
                "productId": product_id,
                "productName": row["name"],
                "mainImage": row.get("mainImage") or "/static/picture/noimg.jpg",
                "price": float(row["price"]),
                "stock": int(stock),
                "sales": int(row["sales"] or 0),
                "categoryName": row.get("categoryName") or "未分类",
                "dailyAvgSales": round(daily_avg, 2),
                "weekSales": int(forecast_qty),
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
        """
        计算补货优先级

        基于"可售天数"判断补货紧急程度：
          可售天数 = 当前库存 ÷ 日均预测销量

        等级划分：
          1-紧急（红色）  : 可售 < 3天 且 有销量 → 不补货将断货
          2-较高（橙色）  : 可售 < 7天 且 日均销量 > 0 → 近期需要补货
          3-一般（黄色）  : 可售 < 14天 → 可持续观察，计划性补货
          4-暂不需（绿色）: 可售 ≥ 14天 → 库存充足

        特别说明：
          - 如果没有历史销量数据（daily_avg=0, week_sales=0），
            即使库存很少也不会判定为紧急，因为可能是新品或滞销品
          - 可售天数 = 999 表示没有销量数据，归为"暂不需"
        """
        if sellable_days < self.RESTOCK_URGENT_DAYS and (week_sales > 0 or daily_avg > 0):
            return 1, "紧急"
        if sellable_days < self.RESTOCK_HIGH_DAYS and daily_avg > 0:
            return 2, "较高"
        if sellable_days < self.RESTOCK_NORMAL_DAYS:
            return 3, "一般"
        return 4, "暂不需补货"

    # ── 季节性推荐 ────────────────────────────────────────

    def _count_seasonal_candidates(self, supplier_id: Optional[int]) -> int:
        """统计季节选品推荐数量（仅计数，轻量查询）"""
        current_month = datetime.now().month
        exclusion_sql = ""
        params: List[Any] = [current_month]
        if supplier_id is not None:
            exclusion_sql = "AND NOT EXISTS (SELECT 1 FROM py_product p2 WHERE p2.supplierId = %s AND p2.status = 1 AND p2.id = p.id)"
            params.append(supplier_id)
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"""
                        SELECT COUNT(DISTINCT p.id) AS cnt
                        FROM py_product p
                        JOIN py_order_item oi ON oi.productId = p.id
                        JOIN py_order o ON oi.orderId = o.id
                        WHERE o.status IN ('paid','shipped','delivered','completed')
                          AND MONTH(STR_TO_DATE(o.createTime, '%%Y-%%m-%%d %%H:%%i:%%s')) = %s
                          AND p.status = 1
                          {exclusion_sql}
                    """, params)
                    return cursor.fetchone()["cnt"] or 0
        except Exception:
            return 0

    def _query_seasonal_products(
        self, supplier_id: Optional[int], limit: int = 20
    ) -> List[Dict[str, Any]]:
        """查询季节性推荐商品"""
        current_month = datetime.now().month

        exclusion_sql = ""
        params: List[Any] = [current_month]
        if supplier_id is not None:
            exclusion_sql = (
                "AND NOT EXISTS ("
                "  SELECT 1 FROM py_product p2"
                "  WHERE p2.supplierId = %s AND p2.status = 1 AND p2.id = p.id"
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
        """一键采购：生成采购订单（按进价计算），而非直接复制商品"""
        ps = PurchaseService()
        return ps.create_order(supplier_id, products)

    # ── 滞销商品折扣 ──────────────────────────────────────────

    def set_slow_moving_discount(
        self, supplier_id: int, product_id: int, discount_rate: float,
    ) -> Dict[str, Any]:
        """设置滞销商品折扣率（discount_rate: 0.00~1.00，如0.8=八折）"""
        if not 0 < discount_rate <= 1:
            return error("折扣率应在 0~1 之间")
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO py_supplier_discount (supplierId, productId, discountRate)
                           VALUES (%s, %s, %s)
                           ON DUPLICATE KEY UPDATE discountRate = %s, updated_at = NOW()""",
                        (supplier_id, product_id, discount_rate, discount_rate),
                    )
                    conn.commit()
                    return success(None, "折扣已设置")
        except Exception as e:
            print(f"设置折扣失败: {e}")
            return error("设置折扣失败")

    def clear_slow_moving_discount(
        self, supplier_id: int, product_id: int,
    ) -> Dict[str, Any]:
        """清除滞销商品折扣"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM py_supplier_discount WHERE supplierId = %s AND productId = %s",
                        (supplier_id, product_id),
                    )
                    conn.commit()
                    return success(None, "折扣已清除")
        except Exception as e:
            print(f"清除折扣失败: {e}")
            return error("清除折扣失败")

    # ── 库存健康度 ─────────────────────────────────────────

    def _compute_inventory_health(
        self, supplier_id: Optional[int],
        slow: Optional[List[Dict[str, Any]]] = None,
        restock: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        计算库存健康度分布

        将全部上架商品分为三类：
          healthy      : 正常商品 = 总数 - 积压商品 - 缺货商品
          overstocked  : 积压商品 = 滞销预警中 riskLevel=high 的商品数
          understocked: 缺货商品 = 补货优先级中 level≤2（紧急+较高）的商品数

        用途：在智能选品看板中用环形图直观展示库存结构，帮助团长
        快速了解当前库存的整体健康状况。
        """
        if slow is None:
            slow = self._query_slow_moving(supplier_id)
        if restock is None:
            restock = self._query_restock_priorities(supplier_id)

        total_on_shelf = 0
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                if supplier_id is not None:
                    cursor.execute(
                        "SELECT COUNT(*) AS cnt FROM py_product WHERE supplierId = %s AND status = 1",
                        (supplier_id,),
                    )
                else:
                    cursor.execute(
                        "SELECT COUNT(*) AS cnt FROM py_product WHERE status = 1"
                    )
                total_on_shelf = cursor.fetchone()["cnt"] or 0

        overstocked = sum(1 for p in slow if p.get("riskLevel") == "high")
        understocked = sum(1 for p in restock if p.get("priorityLevel", 99) <= 2)
        normal = max(0, total_on_shelf - overstocked - understocked)
        return {
            "totalOnShelf": total_on_shelf,
            "healthy": normal,
            "overstocked": overstocked,
            "understocked": understocked,
        }
