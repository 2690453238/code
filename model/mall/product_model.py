"""
商品数据模型
"""
from typing import List, Dict, Optional
from datetime import datetime


class ProductModel:
    """商品模型"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def get_products(self, category_id: int = None, status: int = None, page: int = 1, limit: int = 10, keyword: str = None, sort_type: str = 'default', supplier_id: int = None) -> Dict:
        """获取商品列表"""
        with self.db.cursor() as cursor:
            # 构建查询条件
            where_conditions = []
            params = []
            
            if status is not None:
                where_conditions.append("p.status = %s")
                params.append(status)
            
            if category_id:
                where_conditions.append("p.categoryId = %s")
                params.append(category_id)
            
            if keyword:
                where_conditions.append("(p.name LIKE %s OR p.description LIKE %s)")
                keyword_param = f"%{keyword}%"
                params.extend([keyword_param, keyword_param])

            if supplier_id is not None:
                where_conditions.append("p.supplierId = %s")
                params.append(supplier_id)
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # 查询总数
            count_sql = f"SELECT COUNT(*) as total FROM py_product p WHERE {where_clause}"
            print(f"执行SQL: {count_sql}, 参数: {params}")
            cursor.execute(count_sql, params)
            total = cursor.fetchone()['total']
            
            # 构建排序条件
            order_clause = "ORDER BY p.createTime DESC"
            if sort_type == 'price_asc':
                order_clause = "ORDER BY p.price ASC"
            elif sort_type == 'price_desc':
                order_clause = "ORDER BY p.price DESC"
            elif sort_type == 'sales_desc':
                order_clause = "ORDER BY p.sales DESC"
            
            # 查询数据
            offset = (page - 1) * limit
            data_sql = f"""
                SELECT p.id, p.name, p.description, p.categoryId, p.supplierId, p.brand, p.mainImage, 
                       p.galleryImages, p.price, p.originalPrice, p.stock, p.sales, p.status,
                       p.isHot, p.isNew, p.createTime, p.updateTime,
                       c.name as categoryName
                FROM py_product p
                LEFT JOIN py_category c ON p.categoryId = c.id
                WHERE {where_clause}
                {order_clause}
                LIMIT %s OFFSET %s
            """
            data_params = params + [limit, offset]
            print(f"执行SQL: {data_sql}, 参数: {data_params}")
            cursor.execute(data_sql, data_params)
            rows = cursor.fetchall()
            
            # 转换Decimal类型为float，避免JSON序列化错误
            for row in rows:
                if row.get('price'):
                    row['price'] = float(row['price'])
                if row.get('originalPrice'):
                    row['originalPrice'] = float(row['originalPrice'])
                # 转换datetime类型为字符串，避免JSON序列化错误
                if row.get('createTime'):
                    row['createTime'] = row['createTime'].strftime('%Y-%m-%d %H:%M:%S') if row['createTime'] else None
                if row.get('updateTime'):
                    row['updateTime'] = row['updateTime'].strftime('%Y-%m-%d %H:%M:%S') if row['updateTime'] else None
            
            return {
                'total': total,
                'page': page,
                'limit': limit,
                'rows': rows
            }
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        """根据ID获取商品详情"""
        with self.db.cursor() as cursor:
            sql = """
                SELECT p.id, p.name, p.description, p.categoryId, p.supplierId, p.brand, p.mainImage, 
                       p.galleryImages, p.price, p.originalPrice, p.stock, p.sales, p.status,
                       p.isHot, p.isNew, p.createTime, p.updateTime,
                       c.name as categoryName
                FROM py_product p
                LEFT JOIN py_category c ON p.categoryId = c.id
                WHERE p.id = %s
            """
            print(f"执行SQL: {sql}, 参数: {product_id}")
            cursor.execute(sql, (product_id,))
            result = cursor.fetchone()
            if result:
                # 转换Decimal类型为float，避免JSON序列化错误
                if result.get('price'):
                    result['price'] = float(result['price'])
                if result.get('originalPrice'):
                    result['originalPrice'] = float(result['originalPrice'])
                # 转换datetime类型为字符串，避免JSON序列化错误
                if result.get('createTime'):
                    result['createTime'] = result['createTime'].strftime('%Y-%m-%d %H:%M:%S') if result['createTime'] else None
                if result.get('updateTime'):
                    result['updateTime'] = result['updateTime'].strftime('%Y-%m-%d %H:%M:%S') if result['updateTime'] else None
            return result
    
    def create_product(self, product_data: Dict) -> int:
        """创建商品"""
        try:
            with self.db.cursor() as cursor:
                sql = """
                    INSERT INTO py_product (supplierId, name, description, categoryId, brand, mainImage,
                                          galleryImages, price, costPrice, originalPrice, stock, status, isHot, isNew)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    product_data.get('supplierId'),
                    product_data['name'],
                    product_data.get('description', ''),
                    product_data['categoryId'],
                    product_data.get('brand', ''),
                    product_data.get('mainImage', ''),
                    product_data.get('galleryImages', ''),
                    product_data['price'],
                    product_data.get('costPrice'),
                    product_data.get('originalPrice'),
                    product_data.get('stock', 0),
                    product_data.get('status', 1),
                    product_data.get('isHot', 0),
                    product_data.get('isNew', 0)
                )
                print(f"执行SQL: {sql}, 参数: {params}")
                cursor.execute(sql, params)
                # 添加事务提交
                self.db.commit()
                print(f"商品创建成功，ID: {cursor.lastrowid}")
                return cursor.lastrowid
        except Exception as e:
            print(f"商品创建失败: {str(e)}")
            self.db.rollback()  # 回滚事务
            raise e
    
    def update_product(self, product_id: int, product_data: Dict, supplier_id: int = None) -> bool:
        """更新商品"""
        try:
            with self.db.cursor() as cursor:
                # 构建更新字段
                update_fields = []
                params = []
                
                for field in ['name', 'description', 'categoryId', 'brand', 'mainImage',
                             'galleryImages', 'price', 'costPrice', 'originalPrice', 'stock', 'status', 'isHot', 'isNew']:
                    if field in product_data:
                        update_fields.append(f"{field} = %s")
                        params.append(product_data[field])
                
                if not update_fields:
                    return False
                
                params.append(product_id)
                sql = f"UPDATE py_product SET {', '.join(update_fields)} WHERE id = %s"
                if supplier_id is not None:
                    sql += " AND supplierId = %s"
                    params.append(supplier_id)
                print(f"执行SQL: {sql}, 参数: {params}")
                cursor.execute(sql, params)
                # 添加事务提交
                self.db.commit()
                print(f"商品更新成功，影响行数: {cursor.rowcount}")
                return cursor.rowcount > 0
        except Exception as e:
            print(f"商品更新失败: {str(e)}")
            self.db.rollback()  # 回滚事务
            raise e
    
    def delete_product(self, product_id: int, supplier_id: int = None) -> bool:
        """删除商品（物理删除）"""
        try:
            with self.db.cursor() as cursor:
                sql = "DELETE FROM py_product WHERE id = %s"
                params = [product_id]
                if supplier_id is not None:
                    sql += " AND supplierId = %s"
                    params.append(supplier_id)
                print(f"执行SQL: {sql}, 参数: {product_id}")
                cursor.execute(sql, params)
                # 添加事务提交
                self.db.commit()
                print(f"商品删除成功，影响行数: {cursor.rowcount}")
                return cursor.rowcount > 0
        except Exception as e:
            print(f"商品删除失败: {str(e)}")
            self.db.rollback()  # 回滚事务
            raise e
    
    def update_stock(self, product_id: int, quantity: int) -> bool:
        """更新库存"""
        with self.db.cursor() as cursor:
            sql = "UPDATE py_product SET stock = stock - %s WHERE id = %s AND stock >= %s"
            print(f"执行SQL: {sql}, 参数: {quantity, product_id, quantity}")
            cursor.execute(sql, (quantity, product_id, quantity))
            # 添加事务提交
            self.db.commit()
            print(f"库存更新成功，影响行数: {cursor.rowcount}")
            return cursor.rowcount > 0
    
    def update_product_status(self, product_id: int, status: int, supplier_id: int = None) -> bool:
        """更新商品状态"""
        try:
            with self.db.cursor() as cursor:
                sql = "UPDATE py_product SET status = %s WHERE id = %s"
                params = [status, product_id]
                if supplier_id is not None:
                    sql += " AND supplierId = %s"
                    params.append(supplier_id)
                print(f"执行SQL: {sql}, 参数: {status, product_id}")
                cursor.execute(sql, params)
                # 添加事务提交
                self.db.commit()
                print(f"商品状态更新成功，影响行数: {cursor.rowcount}")
                return cursor.rowcount > 0
        except Exception as e:
            print(f"商品状态更新失败: {str(e)}")
            self.db.rollback()  # 回滚事务
            raise e
    
    def batch_delete_products(self, product_ids: List[int], supplier_id: int = None) -> bool:
        """批量删除商品（物理删除）"""
        try:
            with self.db.cursor() as cursor:
                placeholders = ','.join(['%s'] * len(product_ids))
                sql = f"DELETE FROM py_product WHERE id IN ({placeholders})"
                params = list(product_ids)
                if supplier_id is not None:
                    sql += " AND supplierId = %s"
                    params.append(supplier_id)
                print(f"执行SQL: {sql}, 参数: {product_ids}")
                cursor.execute(sql, params)
                # 添加事务提交
                self.db.commit()
                print(f"批量删除商品成功，影响行数: {cursor.rowcount}")
                return cursor.rowcount > 0
        except Exception as e:
            print(f"批量删除商品失败: {str(e)}")
            self.db.rollback()  # 回滚事务
            raise e
