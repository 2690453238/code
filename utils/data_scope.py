"""
数据权限工具类
用于实现基于角色的数据隔离
"""


class DataScopeUtil:
    """数据权限工具类"""
    
    # 数据权限范围常量
    SCOPE_ALL = 'all'  # 全部数据（管理员）
    SCOPE_SELF = 'self'  # 仅自己的数据（商家、普通用户）
    
    # 角色数据权限映射
    ROLE_DATA_SCOPE = {
        'system_admin': SCOPE_ALL,
        'platform_operator': SCOPE_ALL,
        'community_leader': SCOPE_SELF,
        'user': SCOPE_SELF
    }
    
    @staticmethod
    def get_data_scope(role):
        """
        获取角色的数据权限范围
        
        Args:
            role: 用户角色
            
        Returns:
            数据权限范围
        """
        return DataScopeUtil.ROLE_DATA_SCOPE.get(role, DataScopeUtil.SCOPE_SELF)
    
    @staticmethod
    def build_supplier_condition(user_info, table_alias=''):
        """
        构建商家数据隔离的SQL WHERE条件
        
        Args:
            user_info: 用户信息字典，包含 id 和 role
            table_alias: 表别名，如 'p'、't' 等
            
        Returns:
            SQL WHERE条件字符串
        """
        role = user_info.get('role')
        user_id = user_info.get('id')
        
        # 构建表前缀
        prefix = f"{table_alias}." if table_alias else ""
        
        # 管理员可以看到所有数据
        if role in ['system_admin', 'platform_operator']:
            return ""

        # 社区团长只能看到本社区的数据
        if role == 'community_leader':
            return f"{prefix}supplierId = {user_id}"
        
        # 普通用户只能看到自己的数据
        if role == 'user':
            return f"{prefix}userId = {user_id}"
        
        # 默认返回空条件（安全起见，不返回任何数据）
        return "1 = 0"
    
    @staticmethod
    def build_user_condition(user_info, table_alias=''):
        """
        构建用户数据隔离的SQL WHERE条件（用于用户自己的数据，如订单、地址等）
        
        Args:
            user_info: 用户信息字典，包含 id 和 role
            table_alias: 表别名
            
        Returns:
            SQL WHERE条件字符串
        """
        role = user_info.get('role')
        user_id = user_info.get('id')
        
        # 构建表前缀
        prefix = f"{table_alias}." if table_alias else ""
        
        # 管理员可以看到所有数据
        if role in ['system_admin', 'platform_operator']:
            return ""
        
        # 其他角色只能看到自己的数据
        return f"{prefix}userId = {user_id}"
    
    @staticmethod
    def apply_data_scope(sql, user_info, scope_type='supplier', table_alias=''):
        """
        为SQL语句应用数据权限过滤
        
        Args:
            sql: 原始SQL语句
            user_info: 用户信息字典
            scope_type: 权限类型，'supplier' 或 'user'
            table_alias: 表别名
            
        Returns:
            添加了数据权限过滤的SQL语句
        """
        # 根据权限类型构建条件
        if scope_type == 'supplier':
            condition = DataScopeUtil.build_supplier_condition(user_info, table_alias)
        else:
            condition = DataScopeUtil.build_user_condition(user_info, table_alias)
        
        # 如果没有条件，直接返回原SQL
        if not condition:
            return sql
        
        # 判断SQL中是否已有WHERE子句
        sql_upper = sql.upper()
        if 'WHERE' in sql_upper:
            # 已有WHERE，使用AND连接
            return f"{sql} AND {condition}"
        else:
            # 没有WHERE，添加WHERE
            # 找到ORDER BY、GROUP BY、LIMIT等子句的位置
            insert_pos = len(sql)
            for keyword in ['ORDER BY', 'GROUP BY', 'LIMIT', 'OFFSET']:
                pos = sql_upper.find(keyword)
                if pos != -1 and pos < insert_pos:
                    insert_pos = pos
            
            # 在合适的位置插入WHERE条件
            return f"{sql[:insert_pos]} WHERE {condition} {sql[insert_pos:]}"
    
    @staticmethod
    def set_supplier_id_for_insert(data, user_info):
        """
        为插入数据设置supplierId（商家创建商品、分类时使用）
        
        Args:
            data: 要插入的数据字典
            user_info: 用户信息字典
            
        Returns:
            添加了supplierId的数据字典
        """
        role = user_info.get('role')
        user_id = user_info.get('id')
        
        # 系统管理员/平台运营者创建的数据，supplierId 为 NULL（平台侧）
        if role in ['system_admin', 'platform_operator']:
            data['supplierId'] = None
        # 社区团长创建的数据，supplierId 为当前用户 ID
        elif role == 'community_leader':
            data['supplierId'] = user_id
        
        return data
    
    @staticmethod
    def check_data_permission(user_info, data_supplier_id):
        """
        检查用户是否有权限操作某条数据
        
        Args:
            user_info: 用户信息字典
            data_supplier_id: 数据的supplierId
            
        Returns:
            True表示有权限，False表示无权限
        """
        role = user_info.get('role')
        user_id = user_info.get('id')
        
        # 管理员有所有权限
        if role in ['system_admin', 'platform_operator']:
            return True

        # 社区团长只能操作自己的数据
        if role == 'community_leader':
            return data_supplier_id == user_id
        
        # 其他角色无权限
        return False


# 使用示例
"""
# 1. 在查询商品列表时应用数据权限
user_info = {'id': 1, 'role': 'community_leader'}
sql = "SELECT * FROM py_product WHERE status = 1"
sql = DataScopeUtil.apply_data_scope(sql, user_info, 'supplier', '')
# 结果: SELECT * FROM py_product WHERE status = 1 AND supplierId = 1

# 2. 在创建商品时设置supplierId
product_data = {'name': '测试商品', 'price': 99.99}
product_data = DataScopeUtil.set_supplier_id_for_insert(product_data, user_info)
# 结果: {'name': '测试商品', 'price': 99.99, 'supplierId': 1}

# 3. 在更新/删除前检查权限
data_supplier_id = 1  # 从数据库查询到的数据的supplierId
if DataScopeUtil.check_data_permission(user_info, data_supplier_id):
    # 执行更新/删除操作
    pass
else:
    # 返回无权限错误
    pass
"""

