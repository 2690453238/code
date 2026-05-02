from utils.db_utils import execute_query, execute_insert, execute_update
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BehaviorService:
    """商城用户行为服务类"""
    
    def record_user_behavior(self, user_id, item_id, behavior_type, item_category=None, 
                           user_geohash=None, **kwargs):
        """记录用户行为"""
        try:
            # 生成当前时间（精确到小时）
            current_time = datetime.now()
            time_str = current_time.strftime('%Y-%m-%d %H')
            
            # 插入行为记录（只使用实际表中存在的字段）
            sql = """
                INSERT INTO py_user_browse_history (
                    user_id, item_id, behavior_type, item_category, user_geohash, time
                ) VALUES (
                    %s, %s, %s, %s, %s, %s
                )
            """
            
            params = (
                user_id, item_id, behavior_type, item_category, user_geohash, time_str
            )
            
            result = execute_insert(sql, params)
            
            if result:
                logger.info(f"用户行为记录成功: user_id={user_id}, item_id={item_id}, behavior_type={behavior_type}")
                
            return result
            
        except Exception as e:
            logger.error(f"记录用户行为失败: {e}")
            return None
    
    
    def get_user_behavior_stats(self, user_id, days=30):
        """获取用户行为统计（直接从浏览记录表统计）"""
        try:
            sql = """
                SELECT 
                    DATE(createtime) as stat_date,
                    SUM(CASE WHEN behavior_type = 1 THEN 1 ELSE 0 END) as browse_count,
                    SUM(CASE WHEN behavior_type = 2 THEN 1 ELSE 0 END) as favorite_count,
                    SUM(CASE WHEN behavior_type = 3 THEN 1 ELSE 0 END) as cart_count,
                    SUM(CASE WHEN behavior_type = 4 THEN 1 ELSE 0 END) as purchase_count,
                    COUNT(DISTINCT item_id) as unique_items_viewed,
                    COUNT(DISTINCT item_category) as unique_categories_viewed
                FROM py_user_browse_history 
                WHERE user_id = %s 
                    AND createtime >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY DATE(createtime)
                ORDER BY stat_date DESC
            """
            
            stats = execute_query(sql, (user_id, days))
            
            # 计算总计数据
            total_stats = {
                'total_browse': sum(s['browse_count'] for s in stats),
                'total_favorite': sum(s['favorite_count'] for s in stats),
                'total_cart': sum(s['cart_count'] for s in stats),
                'total_purchase': sum(s['purchase_count'] for s in stats),
                'daily_stats': stats
            }
            
            return total_stats
            
        except Exception as e:
            logger.error(f"获取用户行为统计失败: {e}")
            return {}
    
    def get_user_behavior_history(self, user_id, page=1, limit=20, behavior_type=None):
        """获取用户行为历史"""
        try:
            offset = (page - 1) * limit
            
            # 构建查询条件
            where_conditions = ["user_id = %s"]
            params = [user_id]
            
            if behavior_type:
                where_conditions.append("behavior_type = %s")
                params.append(behavior_type)
            
            where_clause = " AND ".join(where_conditions)
            
            # 查询总数
            count_sql = f"SELECT COUNT(*) as total FROM py_user_browse_history WHERE {where_clause}"
            total_result = execute_query(count_sql, params)
            total = total_result[0]['total'] if total_result else 0
            
            # 查询历史记录
            history_sql = f"""
                SELECT 
                    id, item_id, behavior_type, item_category, user_geohash,
                    time, createtime, updatetime,
                    CASE behavior_type
                        WHEN 1 THEN '浏览'
                        WHEN 2 THEN '收藏'
                        WHEN 3 THEN '加购物车'
                        WHEN 4 THEN '购买'
                    END as behavior_name
                FROM py_user_browse_history 
                WHERE {where_clause}
                ORDER BY createtime DESC
                LIMIT %s OFFSET %s
            """
            
            params.extend([limit, offset])
            history = execute_query(history_sql, params)
            
            return {
                'total': total,
                'page': page,
                'limit': limit,
                'list': history
            }
            
        except Exception as e:
            logger.error(f"获取用户行为历史失败: {e}")
            return {
                'total': 0,
                'page': page,
                'limit': limit,
                'list': []
            }
    
    def get_popular_items(self, page=1, limit=20, category_id=None, days=7):
        """获取热门商品（直接从浏览记录表统计）"""
        try:
            offset = (page - 1) * limit
            
            # 构建查询条件
            where_conditions = ["createtime >= DATE_SUB(NOW(), INTERVAL %s DAY)"]
            params = [days]
            
            if category_id:
                where_conditions.append("item_category = %s")
                params.append(category_id)
            
            where_clause = " AND ".join(where_conditions)
            
            # 查询总数
            count_sql = f"""
                SELECT COUNT(DISTINCT item_id) as total 
                FROM py_user_browse_history 
                WHERE {where_clause}
            """
            total_result = execute_query(count_sql, params)
            total = total_result[0]['total'] if total_result else 0
            
            # 查询热门商品
            popular_sql = f"""
                SELECT 
                    item_id,
                    item_category,
                    COUNT(*) as total_actions,
                    SUM(CASE WHEN behavior_type = 1 THEN 1 ELSE 0 END) as browse_count,
                    SUM(CASE WHEN behavior_type = 2 THEN 1 ELSE 0 END) as favorite_count,
                    SUM(CASE WHEN behavior_type = 3 THEN 1 ELSE 0 END) as cart_count,
                    SUM(CASE WHEN behavior_type = 4 THEN 1 ELSE 0 END) as purchase_count,
                    COUNT(DISTINCT user_id) as unique_visitors,
                    MAX(createtime) as last_active_time,
                    -- 简单的热度分数计算
                    (SUM(CASE WHEN behavior_type = 1 THEN 1 ELSE 0 END) * 0.1 +
                     SUM(CASE WHEN behavior_type = 2 THEN 1 ELSE 0 END) * 0.2 +
                     SUM(CASE WHEN behavior_type = 3 THEN 1 ELSE 0 END) * 0.3 +
                     SUM(CASE WHEN behavior_type = 4 THEN 1 ELSE 0 END) * 0.4) as popularity_score
                FROM py_user_browse_history 
                WHERE {where_clause}
                GROUP BY item_id, item_category
                ORDER BY popularity_score DESC, browse_count DESC
                LIMIT %s OFFSET %s
            """
            
            params.extend([limit, offset])
            popular_items = execute_query(popular_sql, params)
            
            return {
                'total': total,
                'page': page,
                'limit': limit,
                'list': popular_items
            }
            
        except Exception as e:
            logger.error(f"获取热门商品失败: {e}")
            return {
                'total': 0,
                'page': page,
                'limit': limit,
                'list': []
            }
    
    def get_user_interests(self, user_id, limit=20):
        """获取用户兴趣标签（直接从浏览记录表统计）"""
        try:
            sql = """
                SELECT 
                    item_category as category_id,
                    COUNT(*) as browse_count,
                    SUM(CASE WHEN behavior_type = 4 THEN 1 ELSE 0 END) as purchase_count,
                    MAX(createtime) as last_browse_time,
                    -- 简单的兴趣分数计算
                    LEAST(1.0, (COUNT(*) * 0.1 + SUM(CASE WHEN behavior_type = 4 THEN 1 ELSE 0 END) * 0.9) / 10) as interest_score,
                    CASE 
                        WHEN LEAST(1.0, (COUNT(*) * 0.1 + SUM(CASE WHEN behavior_type = 4 THEN 1 ELSE 0 END) * 0.9) / 10) >= 0.8 THEN '高兴趣'
                        WHEN LEAST(1.0, (COUNT(*) * 0.1 + SUM(CASE WHEN behavior_type = 4 THEN 1 ELSE 0 END) * 0.9) / 10) >= 0.5 THEN '中兴趣'
                        WHEN LEAST(1.0, (COUNT(*) * 0.1 + SUM(CASE WHEN behavior_type = 4 THEN 1 ELSE 0 END) * 0.9) / 10) >= 0.2 THEN '低兴趣'
                        ELSE '无兴趣'
                    END as interest_level
                FROM py_user_browse_history 
                WHERE user_id = %s AND item_category IS NOT NULL AND item_category != ''
                GROUP BY item_category
                HAVING browse_count >= 2
                ORDER BY interest_score DESC, browse_count DESC
                LIMIT %s
            """
            
            interests = execute_query(sql, (user_id, limit))
            
            return {
                'user_id': user_id,
                'total_interests': len(interests),
                'interests': interests
            }
            
        except Exception as e:
            logger.error(f"获取用户兴趣失败: {e}")
            return {
                'user_id': user_id,
                'total_interests': 0,
                'interests': []
            }
    
    def get_behavior_analytics(self, start_date=None, end_date=None):
        """获取行为分析数据"""
        try:
            # 如果没有指定日期，默认查询最近7天
            if not start_date:
                start_date = "DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
            else:
                start_date = f"'{start_date}'"
                
            if not end_date:
                end_date = "CURDATE()"
            else:
                end_date = f"'{end_date}'"
            
            # 行为类型分布
            behavior_distribution_sql = f"""
                SELECT 
                    behavior_type,
                    CASE behavior_type
                        WHEN 1 THEN '浏览'
                        WHEN 2 THEN '收藏'
                        WHEN 3 THEN '加购物车'
                        WHEN 4 THEN '购买'
                    END as behavior_name,
                    COUNT(*) as count,
                    ROUND(COUNT(*) * 100.0 / (
                        SELECT COUNT(*) FROM py_user_browse_history 
                        WHERE DATE(browse_time) BETWEEN {start_date} AND {end_date}
                    ), 2) as percentage
                FROM py_user_browse_history 
                WHERE DATE(browse_time) BETWEEN {start_date} AND {end_date}
                GROUP BY behavior_type 
                ORDER BY behavior_type
            """
            
            behavior_distribution = execute_query(behavior_distribution_sql)
            
            # 每日趋势
            daily_trend_sql = f"""
                SELECT 
                    DATE(browse_time) as date,
                    COUNT(*) as total_actions,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT item_id) as unique_items,
                    SUM(CASE WHEN behavior_type = 1 THEN 1 ELSE 0 END) as browse_count,
                    SUM(CASE WHEN behavior_type = 2 THEN 1 ELSE 0 END) as favorite_count,
                    SUM(CASE WHEN behavior_type = 3 THEN 1 ELSE 0 END) as cart_count,
                    SUM(CASE WHEN behavior_type = 4 THEN 1 ELSE 0 END) as purchase_count
                FROM py_user_browse_history 
                WHERE DATE(browse_time) BETWEEN {start_date} AND {end_date}
                GROUP BY DATE(browse_time)
                ORDER BY date
            """
            
            daily_trend = execute_query(daily_trend_sql)
            
            return {
                'behavior_distribution': behavior_distribution,
                'daily_trend': daily_trend,
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                }
            }
            
        except Exception as e:
            logger.error(f"获取行为分析数据失败: {e}")
            return {
                'behavior_distribution': [],
                'daily_trend': [],
                'date_range': {}
            }
    
    def get_user_recent_behaviors(self, user_id, limit=50):
        """获取用户最近的行为记录"""
        try:
            sql = """
                SELECT 
                    id, item_id, behavior_type, item_category, user_geohash,
                    time, createtime,
                    CASE behavior_type
                        WHEN 1 THEN '浏览'
                        WHEN 2 THEN '收藏'
                        WHEN 3 THEN '加购物车'
                        WHEN 4 THEN '购买'
                    END as behavior_name
                FROM py_user_browse_history 
                WHERE user_id = %s
                ORDER BY createtime DESC
                LIMIT %s
            """
            
            behaviors = execute_query(sql, (user_id, limit))
            return behaviors
            
        except Exception as e:
            logger.error(f"获取用户最近行为失败: {e}")
            return []
    
    def get_item_behavior_stats(self, item_id, days=30):
        """获取商品的行为统计"""
        try:
            sql = """
                SELECT 
                    behavior_type,
                    CASE behavior_type
                        WHEN 1 THEN '浏览'
                        WHEN 2 THEN '收藏'
                        WHEN 3 THEN '加购物车'
                        WHEN 4 THEN '购买'
                    END as behavior_name,
                    COUNT(*) as count,
                    COUNT(DISTINCT user_id) as unique_users
                FROM py_user_browse_history 
                WHERE item_id = %s 
                    AND createtime >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY behavior_type
                ORDER BY behavior_type
            """
            
            stats = execute_query(sql, (item_id, days))
            
            # 计算总计
            total_actions = sum(s['count'] for s in stats)
            total_users = len(set(s['unique_users'] for s in stats))
            
            return {
                'item_id': item_id,
                'total_actions': total_actions,
                'total_unique_users': total_users,
                'behavior_stats': stats
            }
            
        except Exception as e:
            logger.error(f"获取商品行为统计失败: {e}")
            return {}
    
    def get_category_behavior_stats(self, category_id, days=30):
        """获取分类的行为统计"""
        try:
            sql = """
                SELECT 
                    behavior_type,
                    CASE behavior_type
                        WHEN 1 THEN '浏览'
                        WHEN 2 THEN '收藏'
                        WHEN 3 THEN '加购物车'
                        WHEN 4 THEN '购买'
                    END as behavior_name,
                    COUNT(*) as count,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT item_id) as unique_items
                FROM py_user_browse_history 
                WHERE item_category = %s 
                    AND createtime >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY behavior_type
                ORDER BY behavior_type
            """
            
            stats = execute_query(sql, (category_id, days))
            
            return {
                'category_id': category_id,
                'behavior_stats': stats
            }
            
        except Exception as e:
            logger.error(f"获取分类行为统计失败: {e}")
            return {}
