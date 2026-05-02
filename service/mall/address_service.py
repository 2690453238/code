"""
地址管理服务
"""
from utils.db_utils import get_db_connection
from utils.response import success, error
import pymysql


class AddressService:
    """地址管理服务类"""
    
    def get_addresses_by_user(self, user_id):
        """获取用户地址列表"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                        SELECT id, name, phone, province, city, district, address, 
                               isDefault, createTime, updateTime
                        FROM py_address 
                        WHERE userId = %s 
                        ORDER BY isDefault DESC, createTime DESC
                    """
                    print(f"执行SQL: {sql}, 参数: {user_id}")
                    cursor.execute(sql, (user_id,))
                    addresses = cursor.fetchall()
                    
                    # 格式化地址数据
                    formatted_addresses = []
                    for addr in addresses:
                        formatted_addresses.append({
                            'id': addr['id'],
                            'name': addr['name'],
                            'phone': addr['phone'],
                            'province': addr['province'],
                            'city': addr['city'],
                            'district': addr['district'],
                            'address': addr['address'],
                            'isDefault': bool(addr['isDefault']),
                            'createTime': addr['createTime'] if addr['createTime'] else '',
                            'updateTime': addr['updateTime'] if addr['updateTime'] else ''
                        })
                    
                    return success(formatted_addresses)
        except Exception as e:
            print(f"获取地址列表失败: {e}")
            return error(f"获取地址列表失败: {str(e)}")
    
    def create_address(self, user_id, data):
        """创建新地址"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 如果设置为默认地址，先取消其他默认地址
                    if data.get('isDefault'):
                        self._clear_default_address(cursor, user_id)
                    
                    sql = """
                        INSERT INTO py_address 
                        (userId, name, phone, province, city, district, address, isDefault, createTime)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """
                    values = (
                        user_id,
                        data['name'],
                        data['phone'],
                        data.get('province', ''),
                        data.get('city', ''),
                        data.get('district', ''),
                        data['address'],
                        1 if data.get('isDefault') else 0
                    )
                    
                    print(f"执行SQL: {sql}, 参数: {values}")
                    cursor.execute(sql, values)
                    conn.commit()
                    
                    address_id = cursor.lastrowid
                    return success({'id': address_id}, '地址创建成功')
        except Exception as e:
            print(f"创建地址失败: {e}")
            return error(f"创建地址失败: {str(e)}")
    
    def get_address_by_id(self, address_id, user_id):
        """获取地址详情"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                        SELECT id, name, phone, province, city, district, address, 
                               isDefault, createTime, updateTime
                        FROM py_address 
                        WHERE id = %s AND userId = %s
                    """
                    print(f"执行SQL: {sql}, 参数: {address_id}, {user_id}")
                    cursor.execute(sql, (address_id, user_id))
                    address = cursor.fetchone()
                    
                    if not address:
                        return error('地址不存在')
                    
                    formatted_address = {
                        'id': address['id'],
                        'name': address['name'],
                        'phone': address['phone'],
                        'province': address['province'],
                        'city': address['city'],
                        'district': address['district'],
                        'address': address['address'],
                        'isDefault': bool(address['isDefault']),
                        'createTime': address['createTime'] if address['createTime'] else '',
                        'updateTime': address['updateTime'] if address['updateTime'] else ''
                    }
                    
                    return success(formatted_address)
        except Exception as e:
            print(f"获取地址详情失败: {e}")
            return error(f"获取地址详情失败: {str(e)}")
    
    def update_address(self, address_id, user_id, data):
        """更新地址"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查地址是否存在且属于当前用户
                    check_sql = "SELECT id FROM py_address WHERE id = %s AND userId = %s"
                    cursor.execute(check_sql, (address_id, user_id))
                    if not cursor.fetchone():
                        return error('地址不存在或无权限')
                    
                    # 如果设置为默认地址，先取消其他默认地址
                    if data.get('isDefault'):
                        self._clear_default_address(cursor, user_id)
                    
                    sql = """
                        UPDATE py_address 
                        SET name = %s, phone = %s, province = %s, city = %s, 
                            district = %s, address = %s, isDefault = %s, updateTime = NOW()
                        WHERE id = %s AND userId = %s
                    """
                    values = (
                        data['name'],
                        data['phone'],
                        data.get('province', ''),
                        data.get('city', ''),
                        data.get('district', ''),
                        data['address'],
                        1 if data.get('isDefault') else 0,
                        address_id,
                        user_id
                    )
                    
                    print(f"执行SQL: {sql}, 参数: {values}")
                    cursor.execute(sql, values)
                    conn.commit()
                    
                    return success(None, '地址更新成功')
        except Exception as e:
            print(f"更新地址失败: {e}")
            return error(f"更新地址失败: {str(e)}")
    
    def delete_address(self, address_id, user_id):
        """删除地址"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查地址是否存在且属于当前用户
                    check_sql = "SELECT id FROM py_address WHERE id = %s AND userId = %s"
                    cursor.execute(check_sql, (address_id, user_id))
                    if not cursor.fetchone():
                        return error('地址不存在或无权限')
                    
                    sql = "DELETE FROM py_address WHERE id = %s AND userId = %s"
                    print(f"执行SQL: {sql}, 参数: {address_id}, {user_id}")
                    cursor.execute(sql, (address_id, user_id))
                    conn.commit()
                    
                    return success(None, '地址删除成功')
        except Exception as e:
            print(f"删除地址失败: {e}")
            return error(f"删除地址失败: {str(e)}")
    
    def set_default_address(self, address_id, user_id):
        """设置默认地址"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查地址是否存在且属于当前用户
                    check_sql = "SELECT id FROM py_address WHERE id = %s AND userId = %s"
                    cursor.execute(check_sql, (address_id, user_id))
                    if not cursor.fetchone():
                        return error('地址不存在或无权限')
                    
                    # 先取消所有默认地址
                    self._clear_default_address(cursor, user_id)
                    
                    # 设置当前地址为默认
                    sql = "UPDATE py_address SET isDefault = 1, updateTime = NOW() WHERE id = %s AND userId = %s"
                    print(f"执行SQL: {sql}, 参数: {address_id}, {user_id}")
                    cursor.execute(sql, (address_id, user_id))
                    conn.commit()
                    
                    return success(None, '设置默认地址成功')
        except Exception as e:
            print(f"设置默认地址失败: {e}")
            return error(f"设置默认地址失败: {str(e)}")
    
    def get_default_address(self, user_id):
        """获取用户默认地址"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                        SELECT id, name, phone, province, city, district, address, 
                               isDefault, createTime, updateTime
                        FROM py_address 
                        WHERE userId = %s AND isDefault = 1
                        LIMIT 1
                    """
                    print(f"执行SQL: {sql}, 参数: {user_id}")
                    cursor.execute(sql, (user_id,))
                    address = cursor.fetchone()
                    
                    if not address:
                        return success(None, '暂无默认地址')
                    
                    formatted_address = {
                        'id': address['id'],
                        'name': address['name'],
                        'phone': address['phone'],
                        'province': address['province'],
                        'city': address['city'],
                        'district': address['district'],
                        'address': address['address'],
                        'isDefault': bool(address['isDefault']),
                        'createTime': address['createTime'] if address['createTime'] else '',
                        'updateTime': address['updateTime'] if address['updateTime'] else ''
                    }
                    
                    return success(formatted_address)
        except Exception as e:
            print(f"获取默认地址失败: {e}")
            return error(f"获取默认地址失败: {str(e)}")
    
    def _clear_default_address(self, cursor, user_id):
        """清除用户的默认地址"""
        sql = "UPDATE py_address SET isDefault = 0 WHERE userId = %s"
        print(f"执行SQL: {sql}, 参数: {user_id}")
        cursor.execute(sql, (user_id,))
