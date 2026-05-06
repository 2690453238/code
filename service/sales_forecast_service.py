"""销量预测服务"""
from __future__ import annotations

import os
import pickle
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from utils.db_utils import get_db_connection
from utils.response import error, success


VALID_ORDER_STATUS: Tuple[str, ...] = ("paid", "shipped", "delivered", "completed")
ARTIFACT_DIR: str = os.path.join("Predictive", "artifacts")
SAFETY_STOCK_RATE: float = 0.15
CHINA_HOLIDAY_MMDD: Set[str] = {
    "01-01",
    "02-14",
    "03-08",
    "05-01",
    "05-02",
    "05-03",
    "06-01",
    "10-01",
    "10-02",
    "10-03",
    "10-04",
    "10-05",
    "10-06",
    "10-07",
    "11-11",
    "12-12",
    "12-25",
}


@dataclass
class ScopeContext:
    """预测范围上下文"""

    scope_type: str
    supplier_id: Optional[int]
    scope_name: str


class SalesForecastService:
    """销量预测服务"""

    def __init__(self) -> None:
        os.makedirs(ARTIFACT_DIR, exist_ok=True)
        self._prediction_cache: Dict[Tuple[Any, ...], pd.DataFrame] = {}

    def train_model(
        self,
        supplier_id: Optional[int] = None,
        forecast_days: int = 7,
        test_days: int = 14,
    ) -> Dict[str, Any]:
        """训练销量预测模型"""
        try:
            scope = self._build_scope_context(supplier_id)
            dataset = self._build_training_dataset(scope.supplier_id)
            if dataset.empty:
                return error("可用于训练的历史销量数据不足")

            split_result = self._split_dataset(dataset, test_days)
            if split_result is None:
                return error("训练样本不足，无法完成模型训练")

            train_x, train_y, test_x, test_y, train_dates, test_dates = split_result
            model = RandomForestRegressor(
                n_estimators=350,
                max_depth=7,
                min_samples_leaf=4,
                min_samples_split=5,
                max_features="sqrt",
                random_state=42,
                n_jobs=-1,
            )
            model.fit(train_x, train_y)
            pred_y = np.clip(model.predict(test_x), a_min=0.0, a_max=None)
            metrics = self._build_metrics(test_y, pred_y)

            artifact = self._build_artifact(
                scope=scope,
                model=model,
                dataset=dataset,
                forecast_days=forecast_days,
                train_dates=train_dates,
                test_dates=test_dates,
                metrics=metrics,
            )
            self._save_artifact(scope, artifact)
            self._prediction_cache.clear()
            return success(self._build_training_response(artifact))
        except ValueError as exc:
            return error(str(exc))
        except Exception as exc:
            return error(f"训练销量预测模型失败: {str(exc)}")

    def get_evaluation(
        self,
        supplier_id: Optional[int] = None,
        forecast_days: int = 7,
        test_days: int = 14,
    ) -> Dict[str, Any]:
        """获取模型评估结果"""
        artifact = self._load_or_train_artifact(supplier_id, forecast_days, test_days)
        if isinstance(artifact, dict) and artifact.get("code"):
            return artifact
        return success(self._build_evaluation_response(artifact))

    def batch_predict(
        self,
        supplier_id: Optional[int] = None,
        forecast_days: int = 7,
        test_days: int = 14,
        product_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """执行批量预测"""
        artifact = self._load_or_train_artifact(supplier_id, forecast_days, test_days)
        if isinstance(artifact, dict) and artifact.get("code"):
            return artifact

        predictions = self._get_cached_forecast(artifact, forecast_days)
        if product_id is not None:
            predictions = predictions[predictions["product_id"] == int(product_id)]
        summary = self._summarize_predictions(predictions, artifact["scope"])
        return success(summary)

    def get_dashboard(
        self,
        supplier_id: Optional[int] = None,
        forecast_days: int = 7,
        test_days: int = 14,
        trend_days: int = 30,
    ) -> Dict[str, Any]:
        """获取销量趋势看板数据"""
        artifact = self._load_or_train_artifact(supplier_id, forecast_days, test_days)
        if isinstance(artifact, dict) and artifact.get("code"):
            return artifact

        predictions = self._get_cached_forecast(artifact, forecast_days)
        history = artifact["history"].copy()
        trend = self._build_trend_series(history, predictions, trend_days)
        overview = self._build_dashboard_overview(history, predictions, artifact)
        category_share = self._aggregate_dimension(predictions, "category_name", "category")
        supplier_share = self._aggregate_dimension(predictions, "supplier_name", "supplier")
        top_products = self._build_top_products(predictions)
        return success(
            {
                "scope": artifact["scope"],
                "overview": overview,
                "trend": trend,
                "categoryForecast": category_share,
                "supplierForecast": supplier_share,
                "topProducts": top_products,
                "metrics": artifact["metrics"],
            }
        )

    def _build_scope_context(self, supplier_id: Optional[int]) -> ScopeContext:
        """构建预测范围"""
        if supplier_id is None:
            return ScopeContext("platform", None, "全平台")
        return ScopeContext("supplier", int(supplier_id), f"社区团长#{int(supplier_id)}")

    def _build_training_dataset(self, supplier_id: Optional[int]) -> pd.DataFrame:
        """构建训练数据集"""
        product_frame = self._fetch_product_frame(supplier_id)
        sales_frame = self._fetch_sales_frame(supplier_id)
        if product_frame.empty or sales_frame.empty:
            return pd.DataFrame()

        # 过滤掉完全没有销量的商品（无法从中学习）
        products_with_sales = sales_frame["product_id"].unique()
        product_frame = product_frame[product_frame["product_id"].isin(products_with_sales)].copy()
        if product_frame.empty:
            return pd.DataFrame()

        calendar_frame = self._build_calendar_frame(product_frame, sales_frame)
        dataset = calendar_frame.merge(
            sales_frame,
            on=["product_id", "sale_date"],
            how="left",
        )
        dataset["quantity"] = dataset["quantity"].fillna(0.0)
        dataset["sales_amount"] = dataset["sales_amount"].fillna(0.0)
        dataset["has_promotion"] = dataset["has_promotion"].fillna(0).astype(int)
        dataset["order_discount_rate"] = dataset["order_discount_rate"].fillna(0.0)
        dataset["discount_rate"] = dataset["discount_rate"].fillna(0.0)
        dataset = dataset.sort_values(["product_id", "sale_date"]).reset_index(drop=True)
        dataset = self._append_time_features(dataset)
        dataset = self._append_lag_features(dataset)
        # 前14天无法构造滞后特征，丢弃；但保留真实销量>0的行（即使滞后特征为NaN也保留）
        dataset = dataset.dropna(subset=["lag_1", "lag_7", "rolling_mean_7"], thresh=2).reset_index(drop=True)
        # 填充剩余的NaN
        numeric_cols = dataset.select_dtypes(include=[np.number]).columns
        dataset[numeric_cols] = dataset[numeric_cols].fillna(0)
        return dataset

    def _fetch_product_frame(self, supplier_id: Optional[int]) -> pd.DataFrame:
        """查询商品基础信息"""
        condition_sql = ""
        params: List[Any] = []
        if supplier_id is not None:
            condition_sql = "AND p.supplierId = %s"
            params.append(supplier_id)

        sql = f"""
            SELECT
                p.id AS product_id,
                COALESCE(p.supplierId, 0) AS supplier_id,
                COALESCE(u.supplierName, '平台自营') AS supplier_name,
                p.name AS product_name,
                p.categoryId AS category_id,
                COALESCE(c.name, '未分类') AS category_name,
                CAST(p.price AS DECIMAL(10, 2)) AS price,
                CAST(COALESCE(p.originalPrice, p.price) AS DECIMAL(10, 2)) AS original_price,
                p.stock AS stock,
                COALESCE(p.isHot, 0) AS is_hot,
                COALESCE(p.isNew, 0) AS is_new,
                CASE
                    WHEN COALESCE(p.originalPrice, 0) > p.price
                    THEN (p.originalPrice - p.price) / p.originalPrice
                    ELSE 0
                END AS discount_rate
            FROM py_product p
            LEFT JOIN py_category c ON p.categoryId = c.id
            LEFT JOIN py_user u ON p.supplierId = u.id
            WHERE p.status = 1
            {condition_sql}
        """
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
        return pd.DataFrame(rows)

    def _fetch_sales_frame(self, supplier_id: Optional[int]) -> pd.DataFrame:
        """查询历史日销量"""
        params: List[Any] = list(VALID_ORDER_STATUS)
        scope_sql = ""
        if supplier_id is not None:
            scope_sql = "AND o.supplierId = %s"
            params.append(supplier_id)

        sql = f"""
            SELECT
                DATE(STR_TO_DATE(o.createTime, '%%Y-%%m-%%d %%H:%%i:%%s')) AS sale_date,
                p.id AS product_id,
                SUM(oi.quantity) AS quantity,
                SUM(oi.totalAmount) AS sales_amount,
                MAX(
                    CASE
                        WHEN COALESCE(o.discountAmount, 0) > 0
                            OR COALESCE(o.couponAmount, 0) > 0
                            OR o.couponId IS NOT NULL
                        THEN 1
                        ELSE 0
                    END
                ) AS has_promotion,
                AVG(
                    CASE
                        WHEN COALESCE(o.totalAmount, 0) > 0
                        THEN (COALESCE(o.discountAmount, 0) + COALESCE(o.couponAmount, 0)) / o.totalAmount
                        ELSE 0
                    END
                ) AS order_discount_rate
            FROM py_order_item oi
            JOIN py_order o ON oi.orderId = o.id
            JOIN py_product p ON oi.productId = p.id
            WHERE o.status IN (%s, %s, %s, %s)
              {scope_sql}
            GROUP BY DATE(STR_TO_DATE(o.createTime, '%%Y-%%m-%%d %%H:%%i:%%s')), p.id
            ORDER BY sale_date, p.id
        """
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
        sales_frame = pd.DataFrame(rows)
        if sales_frame.empty:
            return sales_frame
        sales_frame["sale_date"] = pd.to_datetime(sales_frame["sale_date"])
        sales_frame["quantity"] = sales_frame["quantity"].astype(float)
        sales_frame["sales_amount"] = sales_frame["sales_amount"].astype(float)
        sales_frame["has_promotion"] = sales_frame["has_promotion"].fillna(0).astype(int)
        sales_frame["order_discount_rate"] = sales_frame["order_discount_rate"].fillna(0.0).astype(float)
        return sales_frame

    def _build_calendar_frame(
        self,
        product_frame: pd.DataFrame,
        sales_frame: pd.DataFrame,
    ) -> pd.DataFrame:
        """生成按商品展开的日历框架"""
        date_index = pd.date_range(
            sales_frame["sale_date"].min(),
            sales_frame["sale_date"].max(),
            freq="D",
        )
        calendar = (
            product_frame.assign(_key=1)
            .merge(pd.DataFrame({"sale_date": date_index, "_key": 1}), on="_key")
            .drop(columns="_key")
        )
        return calendar

    def _append_time_features(self, frame: pd.DataFrame) -> pd.DataFrame:
        """补充时间特征"""
        frame["day_of_week"] = frame["sale_date"].dt.dayofweek
        frame["day_of_month"] = frame["sale_date"].dt.day
        frame["month"] = frame["sale_date"].dt.month
        frame["season"] = ((frame["month"] - 1) // 3 + 1).astype(int)
        frame["is_weekend"] = frame["day_of_week"].isin([5, 6]).astype(int)
        frame["is_holiday"] = frame["sale_date"].dt.strftime("%m-%d").isin(CHINA_HOLIDAY_MMDD).astype(int)
        frame["promotion_strength"] = frame[["discount_rate", "order_discount_rate"]].max(axis=1)
        return frame

    def _append_lag_features(self, frame: pd.DataFrame) -> pd.DataFrame:
        """补充滞后特征（增强版）"""
        groups = frame.groupby("product_id")["quantity"]

        # 基础滞后特征
        frame["lag_1"] = groups.shift(1)
        frame["lag_3"] = groups.shift(3)
        frame["lag_7"] = groups.shift(7)
        frame["lag_14"] = groups.shift(14)

        # 滚动窗口特征
        frame["rolling_mean_3"] = groups.shift(1).rolling(3).mean().reset_index(level=0, drop=True)
        frame["rolling_mean_7"] = groups.shift(1).rolling(7).mean().reset_index(level=0, drop=True)
        frame["rolling_mean_14"] = groups.shift(1).rolling(14).mean().reset_index(level=0, drop=True)
        frame["rolling_sum_14"] = groups.shift(1).rolling(14).sum().reset_index(level=0, drop=True)
        frame["rolling_max_7"] = groups.shift(1).rolling(7).max().reset_index(level=0, drop=True)

        # 星期几历史均值（捕捉周期性），使用 transform 避免 apply 索引对齐问题
        frame["dow_avg"] = frame.groupby(["product_id", "day_of_week"])["quantity"].transform("mean")
        # 对数据量少的商品（<7天）回退到商品整体均值，防止过拟合
        product_mean = frame.groupby("product_id")["quantity"].transform("mean")
        insufficient_data = frame.groupby("product_id")["product_id"].transform("size") < 7
        frame.loc[insufficient_data, "dow_avg"] = product_mean
        frame["dow_avg"] = frame["dow_avg"].fillna(product_mean)

        # 近期销售标记：过去7天是否有销量
        frame["recent_sale_7d"] = groups.shift(1).rolling(7).sum().reset_index(level=0, drop=True)
        frame["recent_sale_7d"] = (frame["recent_sale_7d"] > 0).astype(int)

        # 距离上次销售天数
        def _days_since_last(group):
            result = pd.Series([999] * len(group), index=group.index)
            last_sale = None
            for i in range(len(group)):
                if last_sale is not None:
                    result.iloc[i] = i - last_sale
                if group.iloc[i] > 0:
                    last_sale = i
            return result
        frame["days_since_sale"] = frame.groupby("product_id")["quantity"].transform(
            lambda g: _days_since_last(g)
        )
        frame["days_since_sale"] = frame["days_since_sale"].clip(0, 60)

        # 品类均值特征
        cat_col = "category_id"
        if cat_col in frame.columns:
            cat_grp = frame.groupby(["category_id", "sale_date"])["quantity"].transform("mean")
            frame["cat_daily_avg"] = cat_grp

        return frame

    def _split_dataset(
        self,
        dataset: pd.DataFrame,
        test_days: int,
    ) -> Optional[Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, List[str], List[str]]]:
        """按时间划分训练集与测试集"""
        dates = sorted(dataset["sale_date"].dt.strftime("%Y-%m-%d").unique().tolist())
        if len(dates) <= max(10, test_days):
            return None

        effective_test_days = max(7, min(test_days, len(dates) // 3))
        split_dates = dates[-effective_test_days:]
        feature_cols = self._get_feature_columns()
        train_mask = ~dataset["sale_date"].dt.strftime("%Y-%m-%d").isin(split_dates)
        test_mask = ~train_mask
        train_frame = dataset.loc[train_mask]
        test_frame = dataset.loc[test_mask]
        if train_frame.empty or test_frame.empty:
            return None
        return (
            train_frame[feature_cols],
            train_frame["quantity"],
            test_frame[feature_cols],
            test_frame["quantity"],
            sorted(train_frame["sale_date"].dt.strftime("%Y-%m-%d").unique().tolist()),
            split_dates,
        )

    def _build_metrics(self, actual: pd.Series, pred: np.ndarray) -> Dict[str, float]:
        """构建评估指标"""
        actual_values = actual.to_numpy(dtype=float)
        rmse = float(np.sqrt(mean_squared_error(actual_values, pred)))
        mae = float(mean_absolute_error(actual_values, pred))
        denominator = np.where(actual_values == 0, 1.0, actual_values)
        mape = float(np.mean(np.abs((actual_values - pred) / denominator)) * 100)
        return {
            "rmse": round(rmse, 4),
            "mae": round(mae, 4),
            "mape": round(mape, 2),
            "r2": round(float(r2_score(actual_values, pred)), 4),
        }

    def _build_artifact(
        self,
        scope: ScopeContext,
        model: RandomForestRegressor,
        dataset: pd.DataFrame,
        forecast_days: int,
        train_dates: List[str],
        test_dates: List[str],
        metrics: Dict[str, float],
    ) -> Dict[str, Any]:
        """构建模型产物"""
        history_cols = [
            "sale_date",
            "product_id",
            "supplier_id",
            "supplier_name",
            "product_name",
            "category_id",
            "category_name",
            "price",
            "original_price",
            "stock",
            "is_hot",
            "is_new",
            "discount_rate",
            "quantity",
            "sales_amount",
            "has_promotion",
            "order_discount_rate",
            "day_of_week",
            "day_of_month",
            "month",
            "season",
            "is_weekend",
            "is_holiday",
            "promotion_strength",
        ]
        history = dataset[history_cols].copy()
        history = history.drop_duplicates(["sale_date", "product_id"]).reset_index(drop=True)
        return {
            "scope": {
                "type": scope.scope_type,
                "supplierId": scope.supplier_id,
                "scopeName": scope.scope_name,
            },
            "featureColumns": self._get_feature_columns(),
            "forecastDays": int(forecast_days),
            "metrics": metrics,
            "trainDates": train_dates,
            "testDates": test_dates,
            "trainedAt": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "history": history,
            "model": model,
        }

    def _save_artifact(self, scope: ScopeContext, artifact: Dict[str, Any]) -> None:
        """保存模型产物"""
        with open(self._artifact_path(scope.supplier_id), "wb") as file_obj:
            pickle.dump(artifact, file_obj)

    def _artifact_path(self, supplier_id: Optional[int]) -> str:
        """获取模型文件路径"""
        name = "platform" if supplier_id is None else f"supplier_{int(supplier_id)}"
        return os.path.join(ARTIFACT_DIR, f"{name}_sales_forecast.pkl")

    def _load_or_train_artifact(
        self,
        supplier_id: Optional[int],
        forecast_days: int,
        test_days: int,
    ) -> Any:
        """加载或训练模型产物"""
        path = self._artifact_path(supplier_id)
        if not os.path.exists(path):
            train_result = self.train_model(supplier_id, forecast_days, test_days)
            if train_result["code"] != 200:
                return train_result
        with open(path, "rb") as file_obj:
            artifact = pickle.load(file_obj)
        if sorted(artifact.get("featureColumns", [])) != sorted(self._get_feature_columns()):
            train_result = self.train_model(supplier_id, forecast_days, test_days)
            if train_result["code"] != 200:
                return train_result
            with open(path, "rb") as file_obj:
                artifact = pickle.load(file_obj)
        return artifact

    def _get_cached_forecast(self, artifact: Dict[str, Any], forecast_days: int) -> pd.DataFrame:
        """获取缓存预测结果"""
        scope = artifact["scope"]
        cache_key = (
            scope.get("type"),
            scope.get("supplierId"),
            artifact.get("trainedAt"),
            int(forecast_days),
            self._get_forecast_start_date().strftime("%Y-%m-%d"),
        )

        # 1. 内存缓存
        cached_frame = self._prediction_cache.get(cache_key)
        if cached_frame is not None:
            return cached_frame.copy()

        # 2. 磁盘缓存（避免进程重启后重新计算）
        disk_path = self._prediction_cache_path(cache_key)
        if os.path.exists(disk_path):
            with open(disk_path, "rb") as f:
                predictions = pickle.load(f)
            self._prediction_cache[cache_key] = predictions.copy()
            return predictions

        # 3. 从零计算
        predictions = self._forecast_future(artifact, forecast_days)
        self._prediction_cache[cache_key] = predictions.copy()
        # 持久化到磁盘
        try:
            with open(disk_path, "wb") as f:
                pickle.dump(predictions, f)
        except Exception:
            pass
        return predictions

    def _prediction_cache_path(self, cache_key: tuple) -> str:
        """预测结果磁盘缓存路径"""
        scope_type, supplier_id, trained_at, fdays, date_str = cache_key
        safe_key = f"{scope_type}_{supplier_id or 0}_{trained_at}_{fdays}d_{date_str}"
        safe_key = "".join(c if c.isalnum() or c in "_-." else "_" for c in safe_key)
        return os.path.join(ARTIFACT_DIR, f"pred_{safe_key}.pkl")

    def _forecast_future(self, artifact: Dict[str, Any], forecast_days: int) -> pd.DataFrame:
        """递归预测未来销量"""
        model: RandomForestRegressor = artifact["model"]
        history = artifact["history"].copy()
        history["sale_date"] = pd.to_datetime(history["sale_date"])
        feature_cols = artifact["featureColumns"]
        forecast_start_date = self._get_forecast_start_date()
        future_dates = pd.date_range(forecast_start_date, periods=forecast_days, freq="D")

        result_frames: List[pd.DataFrame] = []
        for _, product_frame in history.groupby("product_id", sort=False):
            product_history = self._prepare_product_history(product_frame, forecast_start_date)
            bridge_dates = pd.date_range(
                product_history["sale_date"].max() + pd.Timedelta(days=1),
                forecast_start_date - pd.Timedelta(days=1),
                freq="D",
            )
            for bridge_date in bridge_dates:
                next_row = self._build_future_row(product_history, bridge_date)
                feature_frame = pd.DataFrame([next_row])[feature_cols]
                raw_pred = float(model.predict(feature_frame)[0])
                next_row["predicted_quantity"] = max(raw_pred, 0.0)
                product_history = pd.concat([product_history, pd.DataFrame([next_row])], ignore_index=True)
            for future_date in future_dates:
                next_row = self._build_future_row(product_history, future_date)
                feature_frame = pd.DataFrame([next_row])[feature_cols]
                raw_pred = float(model.predict(feature_frame)[0])
                next_row["predicted_quantity"] = max(raw_pred, 0.0)
                product_history = pd.concat([product_history, pd.DataFrame([next_row])], ignore_index=True)
            future_frame = product_history[product_history["sale_date"].isin(future_dates)].copy()
            result_frames.append(future_frame)
        return pd.concat(result_frames, ignore_index=True) if result_frames else pd.DataFrame()

    def _to_quantity(self, value: float) -> int:
        """转换为非负销量件数"""
        return int(max(round(float(value)), 0))

    def _get_forecast_start_date(self) -> pd.Timestamp:
        """获取预测起始日期"""
        return pd.Timestamp.now().normalize()

    def _prepare_product_history(
        self,
        product_frame: pd.DataFrame,
        forecast_start_date: pd.Timestamp,
    ) -> pd.DataFrame:
        """准备预测可用历史，避免使用今天及之后的数据"""
        product_history = product_frame.sort_values("sale_date").copy()
        available_history = product_history[product_history["sale_date"] < forecast_start_date].copy()
        if not available_history.empty:
            return available_history
        return product_history.head(1).copy()

    def _build_future_row(self, product_history: pd.DataFrame, future_date: pd.Timestamp) -> Dict[str, Any]:
        """构建未来一天的预测特征"""
        base_row = product_history.iloc[-1].to_dict()
        quantity_series = product_history["quantity"].fillna(product_history.get("predicted_quantity", 0.0)).astype(float)
        if "predicted_quantity" in product_history.columns:
            quantity_series = product_history["predicted_quantity"].fillna(product_history["quantity"]).astype(float)

        # 计算星期几均值
        dow = int(future_date.dayofweek)
        current_dow_series = product_history[product_history["day_of_week"] == dow]["quantity"]
        dow_avg = float(current_dow_series.mean()) if len(current_dow_series) > 0 else 0.0

        # 距离上次销售天数（需重置索引，避免 concat 后索引错位）
        recent = product_history.tail(14).reset_index(drop=True)
        non_zero_days = recent[recent["quantity"] > 0]
        if non_zero_days.empty:
            days_since = 15
        else:
            days_since = len(recent) - int(non_zero_days.index[-1])

        # 品类历史日均销量（预测时无法匹配未来日期，改用历史均值）
        cat_val = int(base_row.get("category_id", 0))
        cat_avg = float(product_history[product_history["category_id"] == cat_val]["quantity"].mean()) if cat_val > 0 else 0.0

        return {
            "sale_date": future_date,
            "product_id": int(base_row["product_id"]),
            "supplier_id": int(base_row["supplier_id"]),
            "supplier_name": base_row["supplier_name"],
            "product_name": base_row["product_name"],
            "category_id": int(base_row["category_id"]),
            "category_name": base_row["category_name"],
            "price": float(base_row["price"]),
            "original_price": float(base_row["original_price"]),
            "stock": int(base_row["stock"]),
            "is_hot": int(base_row["is_hot"]),
            "is_new": int(base_row["is_new"]),
            "discount_rate": float(base_row["discount_rate"]),
            "quantity": 0.0,
            "sales_amount": 0.0,
            "has_promotion": int(float(base_row["discount_rate"]) > 0),
            "order_discount_rate": 0.0,
            "day_of_week": dow,
            "day_of_month": int(future_date.day),
            "month": int(future_date.month),
            "season": int((future_date.month - 1) // 3 + 1),
            "is_weekend": int(dow in [5, 6]),
            "is_holiday": int(future_date.strftime("%m-%d") in CHINA_HOLIDAY_MMDD),
            "promotion_strength": float(base_row["discount_rate"]),
            "lag_1": float(quantity_series.iloc[-1]),
            "lag_3": float(quantity_series.iloc[-3]) if len(quantity_series) >= 3 else float(quantity_series.mean()),
            "lag_7": float(quantity_series.iloc[-7]) if len(quantity_series) >= 7 else float(quantity_series.mean()),
            "lag_14": float(quantity_series.iloc[-14]) if len(quantity_series) >= 14 else float(quantity_series.mean()),
            "rolling_mean_3": float(quantity_series.tail(3).mean()),
            "rolling_mean_7": float(quantity_series.tail(7).mean()),
            "rolling_mean_14": float(quantity_series.tail(14).mean()),
            "rolling_sum_14": float(quantity_series.tail(14).sum()),
            "rolling_max_7": float(quantity_series.tail(7).max()),
            "dow_avg": dow_avg,
            "recent_sale_7d": 1 if float(quantity_series.tail(7).sum()) > 0 else 0,
            "days_since_sale": min(days_since, 60),
            "cat_daily_avg": cat_avg,
        }

    def _summarize_predictions(self, predictions: pd.DataFrame, scope: Dict[str, Any]) -> Dict[str, Any]:
        """汇总批量预测结果"""
        if predictions.empty:
            return {"scope": scope, "forecastDays": 0, "dailyTotals": [], "productPredictions": []}

        product_predictions = (
            predictions.groupby(
                ["product_id", "product_name", "supplier_id", "supplier_name", "category_name", "stock"],
                as_index=False,
            )["predicted_quantity"].sum()
            .sort_values("predicted_quantity", ascending=False)
        )
        daily_totals = (
            predictions.groupby("sale_date", as_index=False)["predicted_quantity"].sum()
            .sort_values("sale_date")
        )
        return {
            "scope": scope,
            "forecastDays": int(daily_totals.shape[0]),
            "dailyTotals": [
                {"date": row["sale_date"].strftime("%Y-%m-%d"), "quantity": int(round(row["predicted_quantity"]))}
                for _, row in daily_totals.iterrows()
            ],
            "productPredictions": [
                {
                    "productId": int(row["product_id"]),
                    "productName": row["product_name"],
                    "supplierId": int(row["supplier_id"]),
                    "supplierName": row["supplier_name"],
                    "categoryName": row["category_name"],
                    "forecastQuantity": int(round(row["predicted_quantity"])),
                    "currentStock": int(row["stock"]),
                    "safetyStock": self._build_safety_stock(round(row["predicted_quantity"])),
                    "purchaseAdvice": self._build_purchase_advice(row),
                }
                for _, row in product_predictions.head(50).iterrows()
            ],
        }

    def _build_safety_stock(self, forecast_quantity: float) -> int:
        """计算安全库存"""
        return int(np.ceil(int(forecast_quantity) * SAFETY_STOCK_RATE))

    def _build_purchase_advice(self, row: pd.Series) -> Dict[str, Any]:
        """生成采购建议"""
        forecast_quantity = int(round(row["predicted_quantity"]))
        stock = int(row["stock"])
        safety_stock = self._build_safety_stock(forecast_quantity)
        target_stock = forecast_quantity + safety_stock
        suggested_quantity = max(target_stock - stock, 0)
        return {
            "targetStock": target_stock,
            "suggestedQuantity": suggested_quantity,
            "stockGap": max(forecast_quantity - stock, 0),
            "riskLevel": self._get_stock_risk_level(stock, target_stock),
        }

    def _get_stock_risk_level(self, stock: int, target_stock: int) -> str:
        """判断库存风险等级"""
        if target_stock <= 0:
            return "low"
        stock_rate = stock / target_stock
        if stock_rate < 0.5:
            return "high"
        if stock_rate < 1.0:
            return "medium"
        return "low"

    def _build_trend_series(
        self,
        history: pd.DataFrame,
        predictions: pd.DataFrame,
        trend_days: int,
    ) -> Dict[str, List[Any]]:
        """构建趋势序列"""
        history_totals = (
            history.groupby("sale_date", as_index=False)["quantity"].sum()
            .sort_values("sale_date")
            .tail(trend_days)
        )
        pred_totals = (
            predictions.groupby("sale_date", as_index=False)["predicted_quantity"].sum()
            .sort_values("sale_date")
        )
        return {
            "historyDates": [row["sale_date"].strftime("%Y-%m-%d") for _, row in history_totals.iterrows()],
            "historySales": [int(row["quantity"]) for _, row in history_totals.iterrows()],
            "forecastDates": [row["sale_date"].strftime("%Y-%m-%d") for _, row in pred_totals.iterrows()],
            "forecastSales": [int(round(row["predicted_quantity"])) for _, row in pred_totals.iterrows()],
        }

    def _build_dashboard_overview(
        self,
        history: pd.DataFrame,
        predictions: pd.DataFrame,
        artifact: Dict[str, Any],
    ) -> Dict[str, Any]:
        """构建看板概览"""
        latest_7 = history.groupby("sale_date", as_index=False)["quantity"].sum().sort_values("sale_date").tail(7)
        next_7 = predictions.groupby("sale_date", as_index=False)["predicted_quantity"].sum().sort_values("sale_date").head(7)
        return {
            "scopeName": artifact["scope"]["scopeName"],
            "trainedAt": artifact["trainedAt"],
            "productCount": int(history["product_id"].nunique()),
            "historyTotal": int(history["quantity"].sum()),
            "forecastTotal": int(round(predictions["predicted_quantity"].sum())),
            "last7DaysSales": int(latest_7["quantity"].sum()),
            "next7DaysForecast": int(round(next_7["predicted_quantity"].sum())),
        }

    def _aggregate_dimension(self, predictions: pd.DataFrame, source_col: str, target_name: str) -> List[Dict[str, Any]]:
        """按维度聚合预测结果"""
        if predictions.empty:
            return []
        grouped = (
            predictions.groupby(source_col, as_index=False)["predicted_quantity"].sum()
            .sort_values("predicted_quantity", ascending=False)
        )
        return [
            {target_name: row[source_col], "quantity": int(round(row["predicted_quantity"]))}
            for _, row in grouped.iterrows()
        ]

    def _build_top_products(self, predictions: pd.DataFrame) -> List[Dict[str, Any]]:
        """构建热销预测商品列表"""
        if predictions.empty:
            return []
        grouped = (
            predictions.groupby(["product_id", "product_name", "stock"], as_index=False)["predicted_quantity"].sum()
            .sort_values("predicted_quantity", ascending=False)
            .head(10)
        )
        return [
            {
                "productId": int(row["product_id"]),
                "productName": row["product_name"],
                "forecastQuantity": int(round(row["predicted_quantity"])),
                "purchaseAdvice": self._build_purchase_advice(row),
            }
            for _, row in grouped.iterrows()
        ]

    def _build_training_response(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        """构建训练响应"""
        return {
            "scope": artifact["scope"],
            "trainedAt": artifact["trainedAt"],
            "metrics": artifact["metrics"],
            "featureColumns": artifact["featureColumns"],
            "trainDateRange": self._build_date_range(artifact["trainDates"]),
            "testDateRange": self._build_date_range(artifact["testDates"]),
        }

    def _build_evaluation_response(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        """构建评估响应"""
        return {
            "scope": artifact["scope"],
            "trainedAt": artifact["trainedAt"],
            "metrics": artifact["metrics"],
            "forecastDays": artifact["forecastDays"],
            "trainDateRange": self._build_date_range(artifact["trainDates"]),
            "testDateRange": self._build_date_range(artifact["testDates"]),
        }

    def _build_date_range(self, dates: List[str]) -> Dict[str, Any]:
        """构建日期范围"""
        if not dates:
            return {"start": None, "end": None, "days": 0}
        return {"start": dates[0], "end": dates[-1], "days": len(dates)}

    def _get_feature_columns(self) -> List[str]:
        """获取特征列"""
        return [
            "product_id",
            "supplier_id",
            "category_id",
            "price",
            "stock",
            "is_hot",
            "is_new",
            "discount_rate",
            "day_of_week",
            "day_of_month",
            "month",
            "season",
            "is_weekend",
            "is_holiday",
            "has_promotion",
            "order_discount_rate",
            "promotion_strength",
            "lag_1",
            "lag_3",
            "lag_7",
            "lag_14",
            "rolling_mean_3",
            "rolling_mean_7",
            "rolling_mean_14",
            "rolling_sum_14",
            "rolling_max_7",
            "dow_avg",
            "recent_sale_7d",
            "days_since_sale",
            "cat_daily_avg",
        ]


# 模块级单例，让内存中的 _prediction_cache 跨请求持久化
_forecast_singleton: Optional[SalesForecastService] = None


def get_forecast_service() -> SalesForecastService:
    global _forecast_singleton
    if _forecast_singleton is None:
        _forecast_singleton = SalesForecastService()
    return _forecast_singleton
