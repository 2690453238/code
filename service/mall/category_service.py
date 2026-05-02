"""
商品分类服务层
"""
from typing import List, Dict, Optional
from model.mall.category_model import CategoryModel
from utils.db_utils import get_db_connection
from utils.response import success, error


class CategoryService:
    """商品分类服务"""
    
    def get_all_categories(self) -> Dict:
        """获取所有分类"""
        conn = get_db_connection()
        try:
            category_model = CategoryModel(conn)
            categories = category_model.get_all_categories()
            return success(categories)
        except Exception as e:
            print(f"获取分类列表失败: {str(e)}")
            return error("获取分类列表失败")
        finally:
            conn.close()
    
    def get_category_tree(self) -> Dict:
        """获取分类树形结构"""
        conn = get_db_connection()
        try:
            category_model = CategoryModel(conn)
            categories = category_model.get_all_categories()
            
            # 构建树形结构
            category_dict = {}
            for category in categories:
                category['children'] = []
                category_dict[category['id']] = category
            
            tree = []
            for category in categories:
                if category['parentId'] == 0:
                    tree.append(category)
                else:
                    if category['parentId'] in category_dict:
                        category_dict[category['parentId']]['children'].append(category)
            
            return success(tree)
        except Exception as e:
            print(f"获取分类树失败: {str(e)}")
            return error("获取分类树失败")
        finally:
            conn.close()
    
    def get_category_by_id(self, category_id: int) -> Dict:
        """根据ID获取分类"""
        conn = get_db_connection()
        try:
            category_model = CategoryModel(conn)
            category = category_model.get_category_by_id(category_id)
            if not category:
                return error("分类不存在")
            return success(category)
        except Exception as e:
            print(f"获取分类详情失败: {str(e)}")
            return error("获取分类详情失败")
        finally:
            conn.close()
    
    def create_category(self, name: str, parent_id: int = 0, sort: int = 0) -> Dict:
        """创建分类"""
        conn = get_db_connection()
        try:
            if not name.strip():
                return error("分类名称不能为空")
            
            category_model = CategoryModel(conn)
            category_id = category_model.create_category(name, parent_id, sort)
            return success({"id": category_id}, "分类创建成功")
        except Exception as e:
            print(f"创建分类失败: {str(e)}")
            return error("创建分类失败")
        finally:
            conn.close()
    
    def update_category(self, category_id: int, name: str, sort: int = None) -> Dict:
        """更新分类"""
        conn = get_db_connection()
        try:
            if not name.strip():
                return error("分类名称不能为空")
            
            category_model = CategoryModel(conn)
            result = category_model.update_category(category_id, name, sort)
            if result:
                return success(None, "分类更新成功")
            else:
                return error("分类更新失败")
        except Exception as e:
            print(f"更新分类失败: {str(e)}")
            return error("更新分类失败")
        finally:
            conn.close()
    
    def delete_category(self, category_id: int) -> Dict:
        """删除分类"""
        conn = get_db_connection()
        try:
            category_model = CategoryModel(conn)
            result = category_model.delete_category(category_id)
            if result:
                return success(None, "分类删除成功")
            else:
                return error("分类删除失败")
        except Exception as e:
            print(f"删除分类失败: {str(e)}")
            return error("删除分类失败")
        finally:
            conn.close()
