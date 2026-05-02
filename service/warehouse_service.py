"""仓库管理服务"""
from typing import Any, Dict, List, Optional, Tuple

from utils.db_utils import get_db_connection
from utils.response import error, success, page_response


class WarehouseService:
    """仓库管理服务"""

    def get_warehouse_list(
        self, supplier_id: int, page: int = 1, limit: int = 10, keyword: str = "",
    ) -> Dict[str, Any]:
        """获取仓库商品列表"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    params: List[Any] = [supplier_id]
                    condition = "w.supplierId = %s"
                    if keyword:
                        condition += " AND w.productName LIKE %s"
                        params.append(f"%{keyword}%")

                    cursor.execute(
                        f"SELECT COUNT(*) AS total FROM py_warehouse w WHERE {condition}",
                        params,
                    )
                    total = cursor.fetchone()["total"]

                    offset = (page - 1) * limit
                    cursor.execute(
                        f"""SELECT w.id, w.productId, w.productName, w.quantity,
                                  w.costPrice, w.created_at, w.updated_at
                           FROM py_warehouse w
                           WHERE {condition}
                           ORDER BY w.updated_at DESC
                           LIMIT %s OFFSET %s""",
                        params + [limit, offset],
                    )
                    rows = cursor.fetchall()

                    for r in rows:
                        if r.get("costPrice"):
                            r["costPrice"] = float(r["costPrice"])
                        if r.get("created_at"):
                            r["created_at"] = str(r["created_at"])
                        if r.get("updated_at"):
                            r["updated_at"] = str(r["updated_at"])

                    return page_response(rows, total, page, limit)
        except Exception as e:
            print(f"获取仓库列表失败: {e}")
            return error("获取仓库列表失败")

    def get_warehouse_stats(self, supplier_id: int) -> Dict[str, Any]:
        """获取仓库统计"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """SELECT COUNT(*) AS total_items,
                                 COALESCE(SUM(quantity), 0) AS total_quantity,
                                 COALESCE(SUM(quantity * costPrice), 0) AS total_value
                          FROM py_warehouse
                          WHERE supplierId = %s""",
                        (supplier_id,),
                    )
                    row = cursor.fetchone()
                    return success({
                        "totalItems": row["total_items"],
                        "totalQuantity": int(row["total_quantity"]),
                        "totalValue": float(row["total_value"] or 0),
                    })
        except Exception as e:
            print(f"获取仓库统计失败: {e}")
            return error("获取仓库统计失败")

    def add_to_warehouse(
        self, supplier_id: int, product_id: int, product_name: str,
        quantity: int, cost_price: float,
    ) -> bool:
        """添加商品到仓库（支付后调用）"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO py_warehouse (supplierId, productId, productName, quantity, costPrice)
                           VALUES (%s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE
                               quantity = quantity + %s,
                               costPrice = %s,
                               productName = %s""",
                        (supplier_id, product_id, product_name, quantity, cost_price,
                         quantity, cost_price, product_name),
                    )
                    conn.commit()
                    return True
        except Exception as e:
            print(f"入库失败: {e}")
            return False
