"""
购物车数据模型
"""
from typing import List, Dict, Optional
from datetime import datetime


class CartModel:
    """购物车模型"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def get_cart_by_user(self, user_id: int) -> List[Dict]:
        """获取用户购物车"""
        with self.db.cursor() as cursor:
            sql = """
                SELECT c.id, c.userId, c.productId, c.skuId, c.quantity, c.price, c.createTime,
                       p.name as productName, p.mainImage as productImage,
                       p.stock as skuStock
                FROM py_cart c
                LEFT JOIN py_product p ON c.productId = p.id
                WHERE c.userId = %s
                ORDER BY c.createTime DESC
            """
            print(f"执行SQL: {sql}, 参数: {user_id}")
            cursor.execute(sql, (user_id,))
            result = cursor.fetchall()
            
            # 转换Decimal类型为float，避免JSON序列化异常
            for item in result:
                item['skuName'] = ''
                if item.get('price') is not None:
                    item['price'] = float(item['price'])
                if item.get('skuStock') is not None:
                    item['skuStock'] = int(item['skuStock'])

            return result
    
    def add_to_cart(self, user_id: int, product_id: int, sku_id: int, quantity: int, price: float) -> bool:
        """添加到购物车"""
        with self.db.cursor() as cursor:
            # 检查是否已存在
            if sku_id is None:
                check_sql = (
                    "SELECT id, quantity FROM py_cart "
                    "WHERE userId = %s AND productId = %s AND skuId IS NULL"
                )
                print(f"执行SQL: {check_sql}, 参数: {(user_id, product_id)}")
                cursor.execute(check_sql, (user_id, product_id))
            else:
                check_sql = (
                    "SELECT id, quantity FROM py_cart "
                    "WHERE userId = %s AND productId = %s AND skuId = %s"
                )
                print(f"执行SQL: {check_sql}, 参数: {(user_id, product_id, sku_id)}")
                cursor.execute(check_sql, (user_id, product_id, sku_id))
            existing = cursor.fetchone()
            
            if existing:
                # 更新数量
                new_quantity = existing['quantity'] + quantity
                update_sql = "UPDATE py_cart SET quantity = %s WHERE id = %s"
                print(f"执行SQL: {update_sql}, 参数: {new_quantity, existing['id']}")
                cursor.execute(update_sql, (new_quantity, existing['id']))
            else:
                # 新增记录
                insert_sql = """
                    INSERT INTO py_cart (userId, productId, skuId, quantity, price)
                    VALUES (%s, %s, %s, %s, %s)
                """
                print(f"执行SQL: {insert_sql}, 参数: {user_id, product_id, sku_id, quantity, price}")
                cursor.execute(insert_sql, (user_id, product_id, sku_id, quantity, price))
            
            # 添加事务提交
            self.db.commit()
            print(f"购物车操作成功")
            return True
    
    def update_cart_quantity(self, cart_id: int, quantity: int) -> bool:
        """更新购物车商品数量"""
        with self.db.cursor() as cursor:
            sql = "UPDATE py_cart SET quantity = %s WHERE id = %s"
            print(f"执行SQL: {sql}, 参数: {quantity, cart_id}")
            cursor.execute(sql, (quantity, cart_id))
            # 添加事务提交
            self.db.commit()
            print(f"购物车数量更新成功，影响行数: {cursor.rowcount}")
            return cursor.rowcount > 0
    
    def remove_from_cart(self, cart_id: int) -> bool:
        """从购物车移除商品"""
        with self.db.cursor() as cursor:
            sql = "DELETE FROM py_cart WHERE id = %s"
            print(f"执行SQL: {sql}, 参数: {cart_id}")
            cursor.execute(sql, (cart_id,))
            # 添加事务提交
            self.db.commit()
            print(f"购物车商品移除成功，影响行数: {cursor.rowcount}")
            return cursor.rowcount > 0
    
    def clear_cart(self, user_id: int) -> bool:
        """清空用户购物车"""
        with self.db.cursor() as cursor:
            sql = "DELETE FROM py_cart WHERE userId = %s"
            print(f"执行SQL: {sql}, 参数: {user_id}")
            cursor.execute(sql, (user_id,))
            # 添加事务提交
            self.db.commit()
            print(f"购物车清空成功，影响行数: {cursor.rowcount}")
            return cursor.rowcount > 0
    
    def get_cart_count(self, user_id: int) -> int:
        """获取购物车商品数量"""
        with self.db.cursor() as cursor:
            sql = "SELECT SUM(quantity) as total FROM py_cart WHERE userId = %s"
            print(f"执行SQL: {sql}, 参数: {user_id}")
            cursor.execute(sql, (user_id,))
            result = cursor.fetchone()
            return result['total'] or 0
