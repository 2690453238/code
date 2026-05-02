import logging
import time
from utils.db_utils import execute_query, execute_insert, execute_update

logger = logging.getLogger(__name__)


class AuthService:
    """认证服务类"""

    ROLE_HOME_PAGE = {
        'system_admin': '/admin/index.html',
        'platform_operator': '/admin/data-analytics.html',
        'community_leader': '/admin/mall/mall-products.html',
        'supplier': '/admin/mall/mall-products.html',
        'user': '/front/mall/mall.html'
    }

    def login(self, username, password, role=None):
        """用户登录验证"""
        try:
            sql = """
                SELECT id, username, password, nickname, avatar, role, status,
                       last_login_time, last_login_ip, createtime, updatetime
                FROM py_user
                WHERE username = %s AND status = 'active'
            """
            users = execute_query(sql, (username,))

            if not users:
                logger.warning(f"用户 {username} 不存在或已被禁用")
                return None

            user = users[0]
            if user['password'] != password:
                logger.warning(f"用户 {username} 密码错误")
                return None

            if role and user['role'] != role:
                logger.warning(f"用户 {username} 角色不匹配：期望 {role}，实际 {user['role']}")
                return None

            current_time = time.strftime('%Y-%m-%d %H:%M:%S')
            update_sql = """
                UPDATE py_user
                SET last_login_time = %s, last_login_ip = %s, updatetime = %s
                WHERE id = %s
            """
            execute_update(update_sql, (current_time, '127.0.0.1', current_time, user['id']))

            user_info = {
                'id': user['id'],
                'username': user['username'],
                'nickname': user['nickname'],
                'avatar': user['avatar'],
                'role': user['role'],
                'status': user['status'],
                'last_login_time': user['last_login_time'],
                'createtime': user['createtime']
            }
            logger.info(f"用户 {username} 登录成功")
            return user_info
        except Exception as e:
            logger.error(f"用户登录验证异常: {e}")
            return None

    def register(self, username, password, nickname=None, email=None, phone=None, supplier_code=None, supplier_name=None):
        """用户注册"""
        try:
            check_sql = "SELECT id FROM py_user WHERE username = %s"
            existing_users = execute_query(check_sql, (username,))
            if existing_users:
                logger.warning(f"用户名 {username} 已存在")
                return False

            current_time = time.strftime('%Y-%m-%d %H:%M:%S')
            insert_sql = """
                INSERT INTO py_user
                (username, password, nickname, email, phone, role, status, createtime, updatetime,
                 supplierCode, supplierName)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            execute_insert(
                insert_sql,
                (username, password, nickname, email, phone, 'user', 'active', current_time, current_time,
                 supplier_code, supplier_name)
            )

            logger.info(f"用户 {username} 注册成功，加入社区 {supplier_name}")
            return True
        except Exception as e:
            logger.error(f"用户注册异常: {e}")
            return False

    def get_community_options(self):
        """获取所有社区选项"""
        try:
            sql = """
                SELECT DISTINCT supplierCode, supplierName
                FROM py_user
                WHERE supplierCode IS NOT NULL AND supplierCode != ''
                ORDER BY supplierCode
            """
            return execute_query(sql) or []
        except Exception as e:
            logger.error(f"获取社区选项异常: {e}")
            return []

    def check_username_exists(self, username):
        """检查用户名是否存在"""
        try:
            sql = "SELECT id FROM py_user WHERE username = %s"
            users = execute_query(sql, (username,))
            return len(users) > 0
        except Exception as e:
            logger.error(f"检查用户名存在性异常: {e}")
            return False

    def get_user_by_username(self, username):
        """根据用户名获取用户信息"""
        try:
            sql = """
                SELECT id, username, nickname, avatar, role, status,
                       last_login_time, createtime, updatetime
                FROM py_user
                WHERE username = %s
            """
            users = execute_query(sql, (username,))
            return users[0] if users else None
        except Exception as e:
            logger.error(f"根据用户名获取用户信息异常: {e}")
            return None

    def get_role_home_page(self, role):
        """根据角色获取登录后首页"""
        return self.ROLE_HOME_PAGE.get(role, '/')
