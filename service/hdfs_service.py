"""
HDFS 服务层
提供数据同步到HDFS或本地文件的容错处理逻辑
"""
import os
import csv
import json
import logging
from datetime import datetime
from utils.db_utils import execute_query
from config.config import HDFS_CONFIG

logger = logging.getLogger(__name__)

# 本地降级存储目录
LOCAL_FALLBACK_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'hdfs_local_backup')


def _ensure_local_dir():
    """确保本地备份目录存在"""
    if not os.path.exists(LOCAL_FALLBACK_DIR):
        os.makedirs(LOCAL_FALLBACK_DIR)


def check_hdfs_status():
    """检查HDFS服务是否可用"""
    try:
        from hdfs import InsecureClient
        hdfs_url = f"http://{HDFS_CONFIG['host']}:{HDFS_CONFIG['port']}"
        client = InsecureClient(hdfs_url, user=HDFS_CONFIG['user'])
        # 尝试列出根目录，验证连通性
        client.status('/')
        return {'available': True, 'message': 'HDFS服务正常', 'url': hdfs_url}
    except ImportError:
        return {'available': False, 'message': 'hdfs库未安装'}
    except Exception as e:
        return {'available': False, 'message': str(e)}


def _write_to_local(rows, table_name, fieldnames):
    """
    将数据写入本地CSV文件（降级处理）
    Returns: (file_path, record_count)
    """
    _ensure_local_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{table_name}_{timestamp}.csv"
    file_path = os.path.join(LOCAL_FALLBACK_DIR, filename)

    with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"数据已写入本地文件: {file_path}，共 {len(rows)} 条")
    return file_path, len(rows)


def _write_to_hdfs(rows, table_name, fieldnames):
    """
    将数据写入HDFS
    Returns: (hdfs_path, record_count)
    """
    import io
    from hdfs import InsecureClient

    hdfs_url = f"http://{HDFS_CONFIG['host']}:{HDFS_CONFIG['port']}"
    client = InsecureClient(hdfs_url, user=HDFS_CONFIG['user'])

    base_path = HDFS_CONFIG['hdfs_path']
    date_str = datetime.now().strftime('%Y-%m-%d')
    hdfs_dir = f"{base_path}/{table_name}/date={date_str}"

    # 确保目录存在
    if not client.status(hdfs_dir, strict=False):
        client.makedirs(hdfs_dir)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{table_name}_{timestamp}.csv"
    full_path = f"{hdfs_dir}/{filename}"

    # 构造 CSV 内容
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    csv_content = buf.getvalue()

    with client.write(full_path, encoding='utf-8') as writer_stream:
        writer_stream.write(csv_content)

    logger.info(f"数据已上传HDFS: {full_path}，共 {len(rows)} 条")
    return full_path, len(rows)


# ─────────────────────────────────────────────
# 用户数据同步
# ─────────────────────────────────────────────

USER_FIELDS = [
    'id', 'username', 'nickname', 'sex', 'age', 'phone', 'email',
    'birthday', 'address', 'education', 'profession', 'company',
    'role', 'status', 'last_login_time', 'createtime', 'updatetime'
]


def sync_user_data_to_hdfs():
    """
    同步用户数据到HDFS，HDFS不可用时降级写入本地文件
    Returns: dict with keys: success, message, data(含 storage_type/file_path/record_count)
    """
    sync_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        # 查询用户数据（不含密码等敏感字段）
        sql = """
            SELECT id, username, nickname, sex, age, phone, email,
                   birthday, address, education, profession, company,
                   role, status, last_login_time, createtime, updatetime
            FROM py_user
            ORDER BY id
        """
        rows = execute_query(sql)
        if not rows:
            return {
                'success': True,
                'message': '用户表暂无数据',
                'data': {'record_count': 0, 'sync_time': sync_time, 'storage_type': 'none'}
            }

        # 序列化 datetime 对象
        serialized = []
        for row in rows:
            r = {}
            for k, v in row.items():
                r[k] = v.strftime('%Y-%m-%d %H:%M:%S') if hasattr(v, 'strftime') else v
            serialized.append(r)

        # 先尝试 HDFS
        hdfs_status = check_hdfs_status()
        if hdfs_status['available']:
            try:
                file_path, count = _write_to_hdfs(serialized, 'py_user', USER_FIELDS)
                return {
                    'success': True,
                    'message': f'成功同步 {count} 条用户数据到HDFS',
                    'data': {
                        'record_count': count,
                        'sync_time': sync_time,
                        'storage_type': 'hdfs',
                        'file_path': file_path
                    }
                }
            except Exception as hdfs_err:
                logger.warning(f"HDFS写入失败，降级到本地: {hdfs_err}")

        # 降级：写本地文件
        file_path, count = _write_to_local(serialized, 'py_user', USER_FIELDS)
        storage_hint = '（HDFS不可用，已降级）' if not hdfs_status['available'] else '（HDFS写入异常，已降级）'
        return {
            'success': True,
            'message': f'成功同步 {count} 条用户数据到本地文件 {storage_hint}',
            'data': {
                'record_count': count,
                'sync_time': sync_time,
                'storage_type': 'local',
                'file_path': file_path,
                'hdfs_message': hdfs_status['message']
            }
        }

    except Exception as e:
        logger.error(f"sync_user_data_to_hdfs 异常: {e}")
        return {
            'success': False,
            'message': f'同步失败: {str(e)}',
            'data': {'record_count': 0, 'sync_time': sync_time}
        }


def get_hdfs_sync_history():
    """获取本地降级文件列表（作为同步历史参考）"""
    try:
        _ensure_local_dir()
        files = []
        for fname in sorted(os.listdir(LOCAL_FALLBACK_DIR), reverse=True):
            if not fname.endswith('.csv'):
                continue
            fpath = os.path.join(LOCAL_FALLBACK_DIR, fname)
            stat = os.stat(fpath)
            files.append({
                'filename': fname,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
        return {'success': True, 'data': files, 'message': '获取成功'}
    except Exception as e:
        logger.error(f"获取同步历史失败: {e}")
        return {'success': False, 'data': [], 'message': str(e)}


# ─────────────────────────────────────────────
# 商品数据同步（供 hdfs_controller 兼容调用）
# ─────────────────────────────────────────────

PRODUCT_FIELDS = [
    'id', 'name', 'categoryId', 'price', 'stock', 'sales',
    'status', 'createTime', 'updateTime'
]


def sync_product_data_to_hdfs(sync_date=None):
    """同步商品数据到HDFS，HDFS不可用时降级到本地文件"""
    sync_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        sql = """
            SELECT id, name, categoryId, price, stock, sales, status, createTime, updateTime
            FROM py_product
            ORDER BY id
        """
        rows = execute_query(sql)
        if not rows:
            return {
                'success': True,
                'message': '商品表暂无数据',
                'data': {'record_count': 0, 'sync_time': sync_time}
            }

        serialized = []
        for row in rows:
            r = {}
            for k, v in row.items():
                r[k] = v.strftime('%Y-%m-%d %H:%M:%S') if hasattr(v, 'strftime') else v
            serialized.append(r)

        hdfs_status = check_hdfs_status()
        if hdfs_status['available']:
            try:
                file_path, count = _write_to_hdfs(serialized, 'py_product', PRODUCT_FIELDS)
                return {
                    'success': True,
                    'message': f'成功同步 {count} 条商品数据到HDFS',
                    'data': {'record_count': count, 'sync_time': sync_time,
                             'storage_type': 'hdfs', 'file_path': file_path}
                }
            except Exception as hdfs_err:
                logger.warning(f"HDFS写入失败，降级到本地: {hdfs_err}")

        file_path, count = _write_to_local(serialized, 'py_product', PRODUCT_FIELDS)
        return {
            'success': True,
            'message': f'成功同步 {count} 条商品数据到本地文件（HDFS不可用）',
            'data': {'record_count': count, 'sync_time': sync_time,
                     'storage_type': 'local', 'file_path': file_path}
        }

    except Exception as e:
        logger.error(f"sync_product_data_to_hdfs 异常: {e}")
        return {
            'success': False,
            'message': f'同步失败: {str(e)}',
            'data': {'record_count': 0, 'sync_time': sync_time}
        }


def get_product_sync_history():
    """获取商品同步历史（本地降级文件列表）"""
    try:
        _ensure_local_dir()
        files = [f for f in sorted(os.listdir(LOCAL_FALLBACK_DIR), reverse=True)
                 if f.startswith('py_product') and f.endswith('.csv')]
        result = []
        for fname in files:
            fpath = os.path.join(LOCAL_FALLBACK_DIR, fname)
            stat = os.stat(fpath)
            result.append({
                'filename': fname,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
        return {'success': True, 'data': result, 'message': '获取成功', 'degraded': False}
    except Exception as e:
        logger.error(f"获取商品同步历史失败: {e}")
        return {'success': False, 'data': [], 'message': str(e), 'degraded': True}


# 兼容旧接口名（hdfs_controller 中调用的是 sync_student_data_to_hdfs）
sync_student_data_to_hdfs = sync_user_data_to_hdfs


# ─────────────────────────────────────────────
# 运营统计报告数据同步
# ─────────────────────────────────────────────

def sync_operation_report_to_hdfs():
    """
    同步运营统计报告数据到HDFS，HDFS不可用时降级写入本地文件。
    包含三个数据集：商品分布、用户评价汇总、品类竞争格局。
    Returns: dict with keys: success, message, data
    """
    sync_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    results = []
    total_records = 0
    errors = []

    # 各数据集定义：(查询SQL, 字段列表, 表名标识)
    datasets = [
        (
            """
            SELECT p.id, p.name, c.name AS category_name, p.price, p.stock, p.sales,
                   p.status, p.createTime
            FROM py_product p
            LEFT JOIN py_category c ON p.categoryId = c.id
            ORDER BY p.id
            """,
            ['id', 'name', 'category_name', 'price', 'stock', 'sales', 'status', 'createTime'],
            'report_product_dist'
        ),
        (
            """
            SELECT oi.id, oi.productId AS product_id, oi.productName AS product_name,
                   c.name AS category_name,
                   oi.reviewRating AS rating, oi.reviewContent AS content, oi.reviewTime AS review_time
            FROM py_order_item oi
            LEFT JOIN py_product p ON oi.productId = p.id
            LEFT JOIN py_category c ON p.categoryId = c.id
            WHERE oi.reviewRating IS NOT NULL
            ORDER BY oi.id
            """,
            ['id', 'product_id', 'product_name', 'category_name', 'rating', 'content', 'review_time'],
            'report_review_summary'
        ),
        (
            """
            SELECT c.name AS category,
                   COUNT(DISTINCT p.id)          AS product_count,
                   COUNT(DISTINCT p.supplierId)  AS supplier_count,
                   COUNT(DISTINCT oi.orderId)    AS order_count,
                   COALESCE(SUM(oi.quantity), 0) AS quantity,
                   COALESCE(SUM(oi.quantity * oi.price), 0) AS revenue
            FROM py_category c
            LEFT JOIN py_product p   ON p.categoryId = c.id
            LEFT JOIN py_order_item oi ON oi.productId = p.id
            GROUP BY c.id, c.name
            ORDER BY revenue DESC
            """,
            ['category', 'product_count', 'supplier_count', 'order_count', 'quantity', 'revenue'],
            'report_category_competition'
        ),
    ]

    hdfs_status = check_hdfs_status()
    use_hdfs = hdfs_status['available']

    for sql, fields, table_name in datasets:
        try:
            rows = execute_query(sql)
            if not rows:
                results.append({'table': table_name, 'record_count': 0, 'storage_type': 'skip'})
                continue

            # 序列化 datetime
            serialized = []
            for row in rows:
                r = {}
                for k, v in row.items():
                    r[k] = v.strftime('%Y-%m-%d %H:%M:%S') if hasattr(v, 'strftime') else v
                serialized.append(r)

            storage_type = 'local'
            file_path = ''

            if use_hdfs:
                try:
                    file_path, count = _write_to_hdfs(serialized, table_name, fields)
                    storage_type = 'hdfs'
                except Exception as hdfs_err:
                    logger.warning(f"HDFS写入 {table_name} 失败，降级本地: {hdfs_err}")
                    file_path, count = _write_to_local(serialized, table_name, fields)
            else:
                file_path, count = _write_to_local(serialized, table_name, fields)

            total_records += count
            results.append({
                'table': table_name,
                'record_count': count,
                'storage_type': storage_type,
                'file_path': file_path
            })
        except Exception as e:
            logger.error(f"同步 {table_name} 失败: {e}")
            errors.append(f"{table_name}: {str(e)}")

    storage_label = 'HDFS' if use_hdfs else '本地文件'
    degraded_hint = '' if use_hdfs else f'（HDFS不可用: {hdfs_status["message"]}，已降级）'
    msg = f'运营报告同步完成，共 {total_records} 条记录 → {storage_label}{degraded_hint}'
    if errors:
        msg += f'，{len(errors)} 个数据集同步失败'

    return {
        'success': True,
        'message': msg,
        'data': {
            'total_records': total_records,
            'sync_time': sync_time,
            'storage_type': 'hdfs' if use_hdfs else 'local',
            'hdfs_available': use_hdfs,
            'hdfs_message': hdfs_status['message'],
            'datasets': results,
            'errors': errors
        }
    }


