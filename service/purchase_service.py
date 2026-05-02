"""采购订单管理服务"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from utils.db_utils import get_db_connection
from utils.response import error, page_response, success



class PurchaseService:
    """采购订单管理服务"""

    # ── 订单列表 ──────────────────────────────────────────────

    def get_orders(
        self, supplier_id: int, page: int = 1, limit: int = 10,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取采购订单列表"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    params: List[Any] = [supplier_id]
                    condition = "po.supplierId = %s"
                    if status:
                        condition += " AND po.status = %s"
                        params.append(status)

                    cursor.execute(
                        f"SELECT COUNT(*) AS total FROM py_purchase_order po WHERE {condition}",
                        params,
                    )
                    total = cursor.fetchone()["total"]

                    offset = (page - 1) * limit
                    cursor.execute(
                        f"""SELECT po.id, po.orderNo, po.status, po.totalCost,
                                  po.created_at, po.updated_at
                           FROM py_purchase_order po
                           WHERE {condition}
                           ORDER BY po.created_at DESC
                           LIMIT %s OFFSET %s""",
                        params + [limit, offset],
                    )
                    rows = cursor.fetchall()

                    for r in rows:
                        r["totalCost"] = float(r["totalCost"] or 0)
                        if r.get("created_at"):
                            r["created_at"] = str(r["created_at"])
                        if r.get("updated_at"):
                            r["updated_at"] = str(r["updated_at"])

                    return page_response(rows, total, page, limit)
        except Exception as e:
            print(f"获取采购订单列表失败: {e}")
            return error("获取采购订单列表失败")

    def get_order_detail(self, order_id: int, supplier_id: int) -> Dict[str, Any]:
        """获取采购订单详情"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """SELECT id, orderNo, status, totalCost, created_at, updated_at
                           FROM py_purchase_order
                           WHERE id = %s AND supplierId = %s""",
                        (order_id, supplier_id),
                    )
                    order = cursor.fetchone()
                    if not order:
                        return error("采购订单不存在")
                    order["totalCost"] = float(order["totalCost"] or 0)
                    order["created_at"] = str(order["created_at"])
                    order["updated_at"] = str(order["updated_at"])

                    cursor.execute(
                        """SELECT id, productId, productName, quantity, costPrice, subtotal
                           FROM py_purchase_order_item
                           WHERE orderId = %s""",
                        (order_id,),
                    )
                    items = cursor.fetchall()
                    for item in items:
                        item["costPrice"] = float(item["costPrice"]) if item.get("costPrice") else 0
                        item["subtotal"] = float(item["subtotal"]) if item.get("subtotal") else 0

                    order["items"] = items
                    return success(order)
        except Exception as e:
            print(f"获取采购订单详情失败: {e}")
            return error("获取采购订单详情失败")

    # ── 创建订单 ──────────────────────────────────────────────

    def create_order(
        self, supplier_id: int, products: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """创建采购订单（从智能选品一键采购调用）"""
        if not products:
            return error("请选择要采购的商品")

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 收集所有商品的基础信息（售价、进价）
                    product_ids = [p["productId"] for p in products]
                    placeholders = ",".join(["%s"] * len(product_ids))
                    cursor.execute(
                        f"SELECT id, name, price, costPrice FROM py_product WHERE id IN ({placeholders}) AND status = 1",
                        product_ids,
                    )
                    db_products = {r["id"]: r for r in cursor.fetchall()}

                    # 构建订单明细
                    total_cost = 0.0
                    items: List[Dict[str, Any]] = []
                    for p in products:
                        pid = p["productId"]
                        qty = max(int(p.get("quantity", 10)), 1)
                        prod = db_products.get(pid)
                        if not prod:
                            continue
                        cost_price = float(prod["costPrice"] or prod["price"] * 4 / 5)
                        subtotal = round(cost_price * qty, 2)
                        total_cost += subtotal
                        items.append({
                            "productId": pid,
                            "productName": prod["name"],
                            "quantity": qty,
                            "costPrice": cost_price,
                            "subtotal": subtotal,
                        })

                    if not items:
                        return error("未找到有效的商品")

                    total_cost = round(total_cost, 2)
                    order_no = self._generate_order_no(cursor)

                    # 插入主表
                    cursor.execute(
                        """INSERT INTO py_purchase_order (orderNo, supplierId, status, totalCost)
                           VALUES (%s, %s, 'draft', %s)""",
                        (order_no, supplier_id, total_cost),
                    )
                    order_id = cursor.lastrowid

                    # 插入明细
                    for item in items:
                        cursor.execute(
                            """INSERT INTO py_purchase_order_item
                               (orderId, productId, productName, quantity, costPrice, subtotal)
                               VALUES (%s, %s, %s, %s, %s, %s)""",
                            (order_id, item["productId"], item["productName"],
                             item["quantity"], item["costPrice"], item["subtotal"]),
                        )

                    conn.commit()
                    return success({
                        "orderId": order_id,
                        "orderNo": order_no,
                        "totalCost": total_cost,
                        "status": "draft",
                        "itemCount": len(items),
                    }, "采购订单创建成功，请在采购订单管理中确认")
        except Exception as e:
            print(f"创建采购订单失败: {e}")
            return error(f"创建采购订单失败: {str(e)}")

    # ── 调整订单 ──────────────────────────────────────────────

    def update_order(
        self, order_id: int, supplier_id: int,
        items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """调整采购订单（只能调整草稿状态）"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, status FROM py_purchase_order WHERE id = %s AND supplierId = %s",
                        (order_id, supplier_id),
                    )
                    order = cursor.fetchone()
                    if not order:
                        return error("采购订单不存在")
                    if order["status"] != "draft":
                        return error("只能调整草稿状态的订单")

                    # 更新明细
                    total_cost = 0.0
                    for item in items:
                        item_id = item.get("id")
                        qty = max(int(item.get("quantity", 1)), 1)
                        if item_id:
                            cursor.execute(
                                "SELECT costPrice FROM py_purchase_order_item WHERE id = %s AND orderId = %s",
                                (item_id, order_id),
                            )
                            row = cursor.fetchone()
                            if not row:
                                continue
                            cp = float(row["costPrice"])
                            subtotal = round(cp * qty, 2)
                            cursor.execute(
                                "UPDATE py_purchase_order_item SET quantity = %s, subtotal = %s WHERE id = %s",
                                (qty, subtotal, item_id),
                            )
                            total_cost += subtotal
                        elif item.get("productId"):
                            # 新增商品
                            pid = item["productId"]
                            cursor.execute(
                                "SELECT id, name, costPrice FROM py_product WHERE id = %s AND status = 1",
                                (pid,),
                            )
                            prod = cursor.fetchone()
                            if not prod:
                                continue
                            cp = float(prod["costPrice"] or prod["price"] * 4 / 5)
                            subtotal = round(cp * qty, 2)
                            cursor.execute(
                                """INSERT INTO py_purchase_order_item
                                   (orderId, productId, productName, quantity, costPrice, subtotal)
                                   VALUES (%s, %s, %s, %s, %s, %s)""",
                                (order_id, pid, prod["name"], qty, cp, subtotal),
                            )
                            total_cost += subtotal

                    total_cost = round(total_cost, 2)
                    cursor.execute(
                        "UPDATE py_purchase_order SET totalCost = %s WHERE id = %s",
                        (total_cost, order_id),
                    )
                    conn.commit()
                    return success({"totalCost": total_cost}, "订单已调整")
        except Exception as e:
            print(f"调整采购订单失败: {e}")
            return error(f"调整采购订单失败: {str(e)}")

    # ── 确认订单 ──────────────────────────────────────────────

    def confirm_order(self, order_id: int, supplier_id: int) -> Dict[str, Any]:
        """确认采购订单"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, status FROM py_purchase_order WHERE id = %s AND supplierId = %s",
                        (order_id, supplier_id),
                    )
                    order = cursor.fetchone()
                    if not order:
                        return error("采购订单不存在")
                    if order["status"] != "draft":
                        return error("只能确认草稿状态的订单")

                    cursor.execute(
                        "UPDATE py_purchase_order SET status = 'confirmed' WHERE id = %s",
                        (order_id,),
                    )
                    conn.commit()
                    return success(None, "订单已确认，请进行支付")
        except Exception as e:
            print(f"确认采购订单失败: {e}")
            return error(f"确认采购订单失败: {str(e)}")

    # ── 支付订单 ──────────────────────────────────────────────

    def pay_order(self, order_id: int, supplier_id: int) -> Dict[str, Any]:
        """支付采购订单（按进价计算，支付后入库）"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, status, totalCost FROM py_purchase_order WHERE id = %s AND supplierId = %s",
                        (order_id, supplier_id),
                    )
                    order = cursor.fetchone()
                    if not order:
                        return error("采购订单不存在")
                    if order["status"] != "confirmed":
                        return error("订单未确认，无法支付")

                    # 获取明细
                    cursor.execute(
                        "SELECT productId, productName, quantity, costPrice FROM py_purchase_order_item WHERE orderId = %s",
                        (order_id,),
                    )
                    items = cursor.fetchall()
                    if not items:
                        return error("订单没有商品")

                    # 逐个更新商品库存
                    for item in items:
                        cursor.execute(
                            "UPDATE py_product SET stock = stock + %s WHERE id = %s AND supplierId = %s",
                            (item["quantity"], item["productId"], supplier_id),
                        )

                    # 更新状态
                    cursor.execute(
                        "UPDATE py_purchase_order SET status = 'paid' WHERE id = %s",
                        (order_id,),
                    )
                    conn.commit()
                    return success(None, "支付成功，商品库存已更新")
        except Exception as e:
            print(f"支付采购订单失败: {e}")
            return error(f"支付失败: {str(e)}")

    # ── 取消订单 ──────────────────────────────────────────────

    def cancel_order(self, order_id: int, supplier_id: int) -> Dict[str, Any]:
        """取消采购订单"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE py_purchase_order SET status = 'cancelled' WHERE id = %s AND supplierId = %s AND status = 'draft'",
                        (order_id, supplier_id),
                    )
                    if cursor.rowcount == 0:
                        return error("无法取消该订单（可能不是草稿状态或不存在）")
                    conn.commit()
                    return success(None, "订单已取消")
        except Exception as e:
            print(f"取消采购订单失败: {e}")
            return error(f"取消采购订单失败: {str(e)}")

    # ── 工具方法 ──────────────────────────────────────────────

    def _generate_order_no(self, cursor) -> str:
        """生成采购订单编号"""
        date_str = datetime.now().strftime("%Y%m%d%H%M%S")
        cursor.execute("SELECT COUNT(*) AS cnt FROM py_purchase_order")
        cnt = cursor.fetchone()["cnt"]
        return f"PO{date_str}{cnt + 1:04d}"
