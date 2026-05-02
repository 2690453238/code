import pymysql
from config.config import DB_CONFIG
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """获取数据库连接"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        return connection
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        raise e

def execute_query(sql, params=None):
    """执行查询语句"""
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            logger.info(f"执行SQL: {sql}")
            if params:
                logger.info(f"参数: {params}")
            cursor.execute(sql, params)
            result = cursor.fetchall()
            return result

def execute_update(sql, params=None):
    """执行更新语句"""
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            logger.info(f"执行SQL: {sql}")
            if params:
                logger.info(f"参数: {params}")
            cursor.execute(sql, params)
            connection.commit()
            return cursor.rowcount

def execute_insert(sql, params=None):
    """执行插入语句"""
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            logger.info(f"执行SQL: {sql}")
            if params:
                logger.info(f"参数: {params}")
            cursor.execute(sql, params)
            connection.commit()
            return cursor.lastrowid

def execute_delete(sql, params=None):
    """执行删除语句"""
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            logger.info(f"执行SQL: {sql}")
            if params:
                logger.info(f"参数: {params}")
            cursor.execute(sql, params)
            connection.commit()
            return cursor.rowcount