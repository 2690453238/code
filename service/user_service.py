import logging
import time
from utils.auth_utils import hash_password
from utils.db_utils import execute_query, execute_insert, execute_update, execute_delete
from utils.file_utils import allowed_file, save_file

logger = logging.getLogger(__name__)


class UserService:
    """用户服务类"""

    VALID_ROLES = {'system_admin', 'platform_operator', 'community_leader', 'user'}

    def get_user_list(self, page=1, limit=10, keyword='', role='', status='', exclude_role=None):
        """获取用户列表"""
        try:
            where_conditions = []
            params = []

            if keyword:
                where_conditions.append("(username LIKE %s OR nickname LIKE %s OR email LIKE %s)")
                keyword_param = f"%{keyword}%"
                params.extend([keyword_param, keyword_param, keyword_param])

            if role:
                where_conditions.append("role = %s")
                params.append(role)

            if status:
                where_conditions.append("status = %s")
                params.append(status)

            if exclude_role:
                where_conditions.append("role != %s")
                params.append(exclude_role)

            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)

            count_sql = f"SELECT COUNT(*) as total FROM py_user {where_clause}"
            count_result = execute_query(count_sql, params)
            total = count_result[0]['total'] if count_result else 0

            offset = (page - 1) * limit
            list_sql = f"""
                SELECT id, username, nickname, avatar, sex, age, phone, email,
                       birthday, card, address, education, profession, company,
                       content, remarks, role, status, last_login_time,
                       last_login_ip, createtime, updatetime,
                       supplierCode, supplierName
                FROM py_user
                {where_clause}
                ORDER BY FIELD(role, 'platform_operator', 'community_leader', 'user'),
                         supplierCode IS NULL,
                         supplierCode,
                         FIELD(role, 'community_leader', 'user'),
                         createtime DESC
                LIMIT %s OFFSET %s
            """
            list_params = params + [limit, offset]
            users = execute_query(list_sql, list_params)

            for user in users:
                user.pop('card', None)

            return users, total
        except Exception as e:
            logger.error(f"获取用户列表异常: {e}")
            return [], 0

    def get_user_by_id(self, user_id):
        """根据 ID 获取用户信息"""
        try:
            sql = """
                SELECT id, username, nickname, avatar, sex, age, phone, email,
                       birthday, card, address, education, profession, company,
                       content, remarks, role, status, last_login_time,
                       last_login_ip, createtime, updatetime,
                       supplierCode, supplierName
                FROM py_user
                WHERE id = %s
            """
            users = execute_query(sql, (user_id,))
            if not users:
                return None

            user = users[0]
            user.pop('card', None)
            return user
        except Exception as e:
            logger.error(f"根据 ID 获取用户信息异常: {e}")
            return None

    def update_user(self, user_id, data):
        """更新用户信息"""
        try:
            update_fields = []
            params = []
            allowed_fields = [
                'nickname', 'avatar', 'sex', 'age', 'phone', 'email',
                'birthday', 'address', 'education', 'profession',
                'company', 'content', 'remarks', 'role', 'status',
                'supplierCode', 'supplierName'
            ]

            for field in allowed_fields:
                if field in data and data[field] is not None:
                    if field == 'role' and data[field] not in self.VALID_ROLES:
                        continue
                    update_fields.append(f"{field} = %s")
                    params.append(data[field])

            if not update_fields:
                return False

            update_fields.append("updatetime = %s")
            params.append(time.strftime('%Y-%m-%d %H:%M:%S'))
            params.append(user_id)
            sql = f"UPDATE py_user SET {', '.join(update_fields)} WHERE id = %s"
            result = execute_update(sql, params)
            return result > 0
        except Exception as e:
            logger.error(f"更新用户信息异常: {e}")
            return False

    def delete_user(self, user_id):
        """删除用户"""
        try:
            sql = "DELETE FROM py_user WHERE id = %s"
            result = execute_delete(sql, (user_id,))
            return result > 0
        except Exception as e:
            logger.error(f"删除用户异常: {e}")
            return False

    def change_password(self, user_id, old_password, new_password):
        """用户修改自己的密码"""
        try:
            check_sql = "SELECT password FROM py_user WHERE id = %s"
            users = execute_query(check_sql, (user_id,))
            if not users:
                return False
            if users[0]['password'] != old_password:
                return False

            current_time = time.strftime('%Y-%m-%d %H:%M:%S')
            update_sql = """
                UPDATE py_user
                SET password = %s, updatetime = %s
                WHERE id = %s
            """
            result = execute_update(update_sql, (new_password, current_time, user_id))
            return result > 0
        except Exception as e:
            logger.error(f"修改密码异常: {e}")
            return False

    def reset_user_password(self, user_id, new_password):
        """管理员重置用户密码"""
        try:
            current_time = time.strftime('%Y-%m-%d %H:%M:%S')
            update_sql = """
                UPDATE py_user
                SET password = %s, updatetime = %s
                WHERE id = %s
            """
            result = execute_update(update_sql, (hash_password(new_password), current_time, user_id))
            return result > 0
        except Exception as e:
            logger.error(f"重置用户密码异常: {e}")
            return False

    def upload_avatar(self, user_id, file):
        """上传头像"""
        try:
            if not allowed_file(file.filename):
                return None

            filename = save_file(file)
            if not filename:
                return None

            avatar_url = f"/upload/{filename}"
            current_time = time.strftime('%Y-%m-%d %H:%M:%S')
            update_sql = """
                UPDATE py_user
                SET avatar = %s, updatetime = %s
                WHERE id = %s
            """
            result = execute_update(update_sql, (avatar_url, current_time, user_id))
            if result > 0:
                return avatar_url
            return None
        except Exception as e:
            logger.error(f"上传头像异常: {e}")
            return None

    def add_user(self, data):
        """添加用户"""
        try:
            check_sql = "SELECT id FROM py_user WHERE username = %s"
            existing_users = execute_query(check_sql, (data['username'],))
            if existing_users:
                return False

            role = data.get('role', 'user')
            if role not in self.VALID_ROLES:
                role = 'user'

            current_time = time.strftime('%Y-%m-%d %H:%M:%S')
            insert_sql = """
                INSERT INTO py_user
                (username, password, nickname, email, phone, sex, age, birthday,
                 address, education, profession, company, content, remarks,
                 role, status, createtime, updatetime,
                 supplierCode, supplierName)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            execute_insert(insert_sql, (
                data['username'],
                hash_password(data['password']),
                data['nickname'],
                data.get('email'),
                data.get('phone'),
                data.get('sex'),
                data.get('age'),
                data.get('birthday'),
                data.get('address'),
                data.get('education'),
                data.get('profession'),
                data.get('company'),
                data.get('content'),
                data.get('remarks'),
                role,
                data.get('status', 'active'),
                current_time,
                current_time,
                data.get('supplierCode'),
                data.get('supplierName')
            ))
            return True
        except Exception as e:
            logger.error(f"添加用户异常: {e}")
            return False

    def get_community_options(self):
        """获取所有社区选项（用于下拉选择）"""
        try:
            sql = """
                SELECT communityCode AS supplierCode, communityName AS supplierName
                FROM py_community
                WHERE status = 'active'
                ORDER BY communityCode
            """
            return execute_query(sql) or []
        except Exception as e:
            logger.error(f"获取社区选项异常: {e}")
            return []

    def get_user_statistics(self):
        """获取用户统计信息"""
        try:
            total_sql = "SELECT COUNT(*) as total FROM py_user"
            total_result = execute_query(total_sql)
            total_users = total_result[0]['total'] if total_result else 0

            role_sql = """
                SELECT role, COUNT(*) as count
                FROM py_user
                WHERE status = 'active'
                GROUP BY role
            """
            role_result = execute_query(role_sql)

            status_sql = """
                SELECT status, COUNT(*) as count
                FROM py_user
                GROUP BY status
            """
            status_result = execute_query(status_sql)

            return {
                'total_users': total_users,
                'role_distribution': {item['role']: item['count'] for item in role_result},
                'status_distribution': {item['status']: item['count'] for item in status_result}
            }
        except Exception as e:
            logger.error(f"获取用户统计信息异常: {e}")
            return None
