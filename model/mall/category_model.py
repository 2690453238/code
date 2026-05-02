"""
商品分类数据模型
"""
from typing import List, Dict, Optional
from datetime import datetime


class CategoryModel:
    """商品分类模型"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def get_all_categories(self) -> List[Dict]:
        """获取所有分类"""
        with self.db.cursor() as cursor:
            sql = """
                SELECT id, name, parentId, level, sort, status, createTime, updateTime
                FROM py_category 
                WHERE status = 1 
                ORDER BY sort ASC, id ASC
            """
            print(f"执行SQL: {sql}")
            cursor.execute(sql)
            return cursor.fetchall()
    
    def get_category_by_id(self, category_id: int) -> Optional[Dict]:
        """根据ID获取分类"""
        with self.db.cursor() as cursor:
            sql = """
                SELECT id, name, parentId, level, sort, status, createTime, updateTime
                FROM py_category 
                WHERE id = %s
            """
            print(f"执行SQL: {sql}, 参数: {category_id}")
            cursor.execute(sql, (category_id,))
            return cursor.fetchone()
    
    def get_categories_by_parent(self, parent_id: int = 0) -> List[Dict]:
        """获取指定父分类下的子分类"""
        with self.db.cursor() as cursor:
            sql = """
                SELECT id, name, parentId, level, sort, status, createTime, updateTime
                FROM py_category 
                WHERE parentId = %s AND status = 1 
                ORDER BY sort ASC, id ASC
            """
            print(f"执行SQL: {sql}, 参数: {parent_id}")
            cursor.execute(sql, (parent_id,))
            return cursor.fetchall()
    
    def create_category(self, name: str, parent_id: int = 0, sort: int = 0) -> int:
        """创建分类"""
        with self.db.cursor() as cursor:
            # 计算层级
            level = 1
            if parent_id > 0:
                parent_sql = "SELECT level FROM py_category WHERE id = %s"
                cursor.execute(parent_sql, (parent_id,))
                parent = cursor.fetchone()
                if parent:
                    level = parent['level'] + 1
            
            sql = """
                INSERT INTO py_category (name, parentId, level, sort, status)
                VALUES (%s, %s, %s, %s, 1)
            """
            print(f"执行SQL: {sql}, 参数: {name, parent_id, level, sort}")
            cursor.execute(sql, (name, parent_id, level, sort))
            # 添加事务提交
            self.db.commit()
            print(f"分类创建成功，ID: {cursor.lastrowid}")
            return cursor.lastrowid
    
    def update_category(self, category_id: int, name: str, sort: int = None) -> bool:
        """更新分类"""
        with self.db.cursor() as cursor:
            if sort is not None:
                sql = "UPDATE py_category SET name = %s, sort = %s WHERE id = %s"
                params = (name, sort, category_id)
            else:
                sql = "UPDATE py_category SET name = %s WHERE id = %s"
                params = (name, category_id)
            
            print(f"执行SQL: {sql}, 参数: {params}")
            cursor.execute(sql, params)
            # 添加事务提交
            self.db.commit()
            print(f"分类更新成功，影响行数: {cursor.rowcount}")
            return cursor.rowcount > 0
    
    def delete_category(self, category_id: int) -> bool:
        """删除分类（软删除）"""
        with self.db.cursor() as cursor:
            sql = "UPDATE py_category SET status = 0 WHERE id = %s"
            print(f"执行SQL: {sql}, 参数: {category_id}")
            cursor.execute(sql, (category_id,))
            # 添加事务提交
            self.db.commit()
            print(f"分类删除成功，影响行数: {cursor.rowcount}")
            return cursor.rowcount > 0
