"""
购物车服务层
"""
from typing import List, Dict, Optional
from model.mall.cart_model import CartModel
from model.mall.product_model import ProductModel
from utils.db_utils import get_db_connection
from utils.response import success, error


class CartService:
    """购物车服务"""
    
    def get_cart_by_user(self, user_id: int) -> Dict:
        """获取用户购物车"""
        try:
            with get_db_connection() as conn:
                cart_model = CartModel(conn)
                cart_items = cart_model.get_cart_by_user(user_id)
                return success(cart_items)
        except Exception as e:
            print(f"获取购物车失败: {str(e)}")
            return error("获取购物车失败")
    
    def add_to_cart(self, user_id: int, product_id: int, sku_id: int = None, quantity: int = 1) -> Dict:
        """添加到购物车"""
        try:
            with get_db_connection() as conn:
                cart_model = CartModel(conn)
                product_model = ProductModel(conn)
                
                # 验证商品是否存在
                product = product_model.get_product_by_id(product_id)
                if not product:
                    return error("商品不存在")
                
                if product['status'] != 1:
                    return error("商品已下架")
                
                # 验证库存
                if product['stock'] < quantity:
                    return error("库存不足")
                
                # 计算价格
                price = product['price']
                
                # 如果有规格，获取规格价格
                if sku_id:
                    # 这里需要实现获取规格价格的逻辑
                    pass
                
                result = cart_model.add_to_cart(user_id, product_id, sku_id, quantity, price)
                if result:
                    return success(None, "添加到购物车成功")
                else:
                    return error("添加到购物车失败")
        except Exception as e:
            print(f"添加到购物车失败: {str(e)}")
            return error("添加到购物车失败")
    
    def update_cart_quantity(self, cart_id: int, quantity: int) -> Dict:
        """更新购物车商品数量"""
        try:
            if quantity <= 0:
                return error("数量必须大于0")
            
            with get_db_connection() as conn:
                cart_model = CartModel(conn)
                result = cart_model.update_cart_quantity(cart_id, quantity)
                if result:
                    return success(None, "更新数量成功")
                else:
                    return error("更新数量失败")
        except Exception as e:
            print(f"更新购物车数量失败: {str(e)}")
            return error("更新购物车数量失败")
    
    def remove_from_cart(self, cart_id: int) -> Dict:
        """从购物车移除商品"""
        try:
            with get_db_connection() as conn:
                cart_model = CartModel(conn)
                result = cart_model.remove_from_cart(cart_id)
                if result:
                    return success(None, "移除商品成功")
                else:
                    return error("移除商品失败")
        except Exception as e:
            print(f"移除购物车商品失败: {str(e)}")
            return error("移除购物车商品失败")
    
    def clear_cart(self, user_id: int) -> Dict:
        """清空购物车"""
        try:
            with get_db_connection() as conn:
                cart_model = CartModel(conn)
                result = cart_model.clear_cart(user_id)
                if result:
                    return success(None, "清空购物车成功")
                else:
                    return error("清空购物车失败")
        except Exception as e:
            print(f"清空购物车失败: {str(e)}")
            return error("清空购物车失败")
    
    def get_cart_count(self, user_id: int) -> Dict:
        """获取购物车商品数量"""
        try:
            with get_db_connection() as conn:
                cart_model = CartModel(conn)
                count = cart_model.get_cart_count(user_id)
                return success({"count": count})
        except Exception as e:
            print(f"获取购物车数量失败: {str(e)}")
            return error("获取购物车数量失败")
