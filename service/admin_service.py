"""
系统管理员服务层
实现系统管理员对社区团长账户的管理逻辑
"""
from utils.db_utils import get_db_connection


class AdminService:
    """系统管理员服务类"""

    COMMUNITY_ROLE = 'community_leader'

    @staticmethod
    def get_suppliers(page_num=1, page_size=10, keyword='', supplier_status=''):
        """获取社区团长列表"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                conditions = [f"role = '{AdminService.COMMUNITY_ROLE}'"]
                params = []

                if keyword:
                    conditions.append("(username LIKE %s OR supplierName LIKE %s OR supplierCode LIKE %s)")
                    params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])

                if supplier_status:
                    conditions.append("supplierStatus = %s")
                    params.append(supplier_status)

                where_clause = " AND ".join(conditions)
                count_sql = f"SELECT COUNT(*) as total FROM py_user WHERE {where_clause}"
                cursor.execute(count_sql, params)
                total = cursor.fetchone()['total']

                offset = (page_num - 1) * page_size
                data_sql = f"""
                    SELECT id, username, nickname, phone, email,
                           supplierName, supplierCode, supplierStatus,
                           supplierLicense, supplierContact, supplierContactPhone,
                           status, createtime, updatetime
                    FROM py_user
                    WHERE {where_clause}
                    ORDER BY createtime DESC
                    LIMIT %s OFFSET %s
                """
                data_params = params + [page_size, offset]
                cursor.execute(data_sql, data_params)
                rows = cursor.fetchall()

                return {
                    'total': total,
                    'pageNum': page_num,
                    'pageSize': page_size,
                    'rows': rows
                }
        finally:
            conn.close()

    @staticmethod
    def create_supplier(data):
        """创建社区团长"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM py_user WHERE username = %s", (data['username'],))
                if cursor.fetchone()['count'] > 0:
                    return {'success': False, 'message': '用户名已存在'}

                cursor.execute("SELECT COUNT(*) as count FROM py_user WHERE supplierCode = %s", (data['supplierCode'],))
                if cursor.fetchone()['count'] > 0:
                    return {'success': False, 'message': '社区编码已存在'}

                sql = """
                    INSERT INTO py_user (
                        username, password, nickname, phone, email, role,
                        supplierName, supplierCode, supplierStatus,
                        supplierLicense, supplierContact, supplierContactPhone,
                        status, createtime, updatetime
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                    )
                """
                params = (
                    data['username'],
                    data['password'],
                    data.get('nickname', ''),
                    data.get('phone', ''),
                    data.get('email', ''),
                    AdminService.COMMUNITY_ROLE,
                    data['supplierName'],
                    data['supplierCode'],
                    data.get('supplierStatus', 'pending'),
                    data.get('supplierLicense', ''),
                    data['supplierContact'],
                    data['supplierContactPhone'],
                    data.get('status', 'active')
                )
                cursor.execute(sql, params)
                conn.commit()
                return {'success': True, 'id': cursor.lastrowid}
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': str(e)}
        finally:
            conn.close()

    @staticmethod
    def update_supplier(supplier_id, data):
        """更新社区团长信息"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                update_fields = []
                params = []
                field_mapping = {
                    'nickname': 'nickname',
                    'phone': 'phone',
                    'email': 'email',
                    'supplierName': 'supplierName',
                    'supplierCode': 'supplierCode',
                    'supplierStatus': 'supplierStatus',
                    'supplierLicense': 'supplierLicense',
                    'supplierContact': 'supplierContact',
                    'supplierContactPhone': 'supplierContactPhone',
                    'status': 'status'
                }

                for key, field in field_mapping.items():
                    if key in data:
                        update_fields.append(f"{field} = %s")
                        params.append(data[key])

                if not update_fields:
                    return {'success': False, 'message': '没有需要更新的字段'}

                update_fields.append("updatetime = NOW()")
                params.append(supplier_id)
                sql = f"""
                    UPDATE py_user
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND role = '{AdminService.COMMUNITY_ROLE}'
                """
                cursor.execute(sql, params)
                conn.commit()
                if cursor.rowcount > 0:
                    return {'success': True}
                return {'success': False, 'message': '社区团长不存在或更新失败'}
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': str(e)}
        finally:
            conn.close()

    @staticmethod
    def delete_supplier(supplier_id):
        """删除社区团长"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM py_product WHERE supplierId = %s", (supplier_id,))
                product_count = cursor.fetchone()['count']
                if product_count > 0:
                    return {'success': False, 'message': f'该社区团长下还有{product_count}个商品，无法删除'}

                sql = f"DELETE FROM py_user WHERE id = %s AND role = '{AdminService.COMMUNITY_ROLE}'"
                cursor.execute(sql, (supplier_id,))
                conn.commit()
                if cursor.rowcount > 0:
                    return {'success': True}
                return {'success': False, 'message': '社区团长不存在或删除失败'}
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': str(e)}
        finally:
            conn.close()

    @staticmethod
    def update_supplier_status(supplier_id, supplier_status):
        """更新社区团长审核状态"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                sql = f"""
                    UPDATE py_user
                    SET supplierStatus = %s, updatetime = NOW()
                    WHERE id = %s AND role = '{AdminService.COMMUNITY_ROLE}'
                """
                cursor.execute(sql, (supplier_status, supplier_id))
                conn.commit()
                if cursor.rowcount > 0:
                    return {'success': True}
                return {'success': False, 'message': '社区团长不存在或更新失败'}
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': str(e)}
        finally:
            conn.close()

    @staticmethod
    def update_account_status(supplier_id, status):
        """更新社区团长账号状态"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                sql = f"""
                    UPDATE py_user
                    SET status = %s, updatetime = NOW()
                    WHERE id = %s AND role = '{AdminService.COMMUNITY_ROLE}'
                """
                cursor.execute(sql, (status, supplier_id))
                conn.commit()
                if cursor.rowcount > 0:
                    return {'success': True}
                return {'success': False, 'message': '社区团长不存在或更新失败'}
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': str(e)}
        finally:
            conn.close()
