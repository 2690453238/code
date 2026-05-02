"""
仪表盘服务层
处理仪表盘相关的数据查询和统计逻辑
"""
from datetime import datetime, timedelta
from utils.db_utils import get_db_connection


class DashboardService:
    """仪表盘服务类"""

    ROLE_LABELS = {
        'system_admin': '系统管理员',
        'platform_operator': '平台运营者',
        'community_leader': '社区团长',
        'user': '普通用户'
    }

    @staticmethod
    def get_user_statistics():
        """获取用户统计数据"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) as total FROM py_user WHERE status = 'active'")
                    total_users = cursor.fetchone()['total']

                    cursor.execute("SELECT COUNT(*) as total FROM py_user WHERE role = 'system_admin' AND status = 'active'")
                    system_admin_count = cursor.fetchone()['total']

                    cursor.execute("SELECT COUNT(*) as total FROM py_user WHERE role = 'platform_operator' AND status = 'active'")
                    platform_operator_count = cursor.fetchone()['total']

                    cursor.execute("SELECT COUNT(*) as total FROM py_user WHERE role = 'community_leader' AND status = 'active'")
                    community_leader_count = cursor.fetchone()['total']

                    cursor.execute("SELECT COUNT(*) as total FROM py_user WHERE role = 'user' AND status = 'active'")
                    normal_users = cursor.fetchone()['total']

                    today = datetime.now().strftime('%Y-%m-%d')
                    cursor.execute("SELECT COUNT(*) as total FROM py_user WHERE DATE(createtime) = %s", (today,))
                    today_users = cursor.fetchone()['total']

                    return {
                        'total_users': total_users,
                        'admin_users': system_admin_count,
                        'normal_users': normal_users,
                        'today_users': today_users,
                        'system_admin_count': system_admin_count,
                        'platform_operator_count': platform_operator_count,
                        'community_leader_count': community_leader_count,
                        'user_count': normal_users
                    }
        except Exception as e:
            print(f"获取用户统计失败: {e}")
            return {
                'total_users': 0,
                'admin_users': 0,
                'normal_users': 0,
                'today_users': 0,
                'system_admin_count': 0,
                'platform_operator_count': 0,
                'community_leader_count': 0,
                'user_count': 0
            }

    @staticmethod
    def get_user_trend_data(days=30):
        """获取用户注册趋势数据"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=days - 1)
                    date_list = []
                    current_date = start_date

                    while current_date <= end_date:
                        date_list.append(current_date.strftime('%Y-%m-%d'))
                        current_date += timedelta(days=1)

                    trend_data = []
                    for date_str in date_list:
                        cursor.execute("""
                            SELECT COUNT(*) as count
                            FROM py_user
                            WHERE DATE(createtime) = %s AND status = 'active'
                        """, (date_str,))
                        trend_data.append(cursor.fetchone()['count'])

                    return {'dates': date_list, 'data': trend_data}
        except Exception as e:
            print(f"获取用户趋势数据失败: {e}")
            return {'dates': [], 'data': []}

    @staticmethod
    def get_role_distribution():
        """获取用户角色分布数据"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT role, COUNT(*) as count
                        FROM py_user
                        WHERE status = 'active'
                        GROUP BY role
                    """)
                    results = cursor.fetchall()
                    return [
                        {
                            'name': DashboardService.ROLE_LABELS.get(item['role'], item['role']),
                            'value': item['count']
                        }
                        for item in results
                    ]
        except Exception as e:
            print(f"获取角色分布数据失败: {e}")
            return []

    @staticmethod
    def get_dashboard_overview():
        """获取仪表盘总览数据"""
        try:
            return {
                'user_stats': DashboardService.get_user_statistics(),
                'announcement_stats': 0,
                'user_trend': DashboardService.get_user_trend_data(7),
                'role_distribution': DashboardService.get_role_distribution(),
                'recent_activities': 0
            }
        except Exception as e:
            print(f"获取仪表盘总览数据失败: {e}")
            return {
                'user_stats': {
                    'total_users': 0,
                    'admin_users': 0,
                    'normal_users': 0,
                    'today_users': 0
                },
                'announcement_stats': {'total_announcements': 0, 'today_announcements': 0, 'top_announcements': 0},
                'user_trend': {'dates': [], 'data': []},
                'role_distribution': [],
                'recent_activities': []
            }
