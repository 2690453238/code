"""
新闻公告服务层
"""
import pymysql
from datetime import datetime
from utils.db_utils import get_db_connection
from utils.response import success, error, page_response


class AnnouncementService:
    """新闻公告服务类"""
    
    @staticmethod
    def get_announcement_list(page_num=1, page_size=10, status=None, keyword=None):
        """
        获取公告列表（分页）
        
        Args:
            page_num: 页码
            page_size: 每页数量
            status: 状态筛选（1-发布，0-草稿）
            keyword: 关键词搜索
            
        Returns:
            dict: 分页响应数据
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 构建查询条件
                    where_conditions = []
                    params = []
                    
                    if status is not None:
                        where_conditions.append("status = %s")
                        params.append(status)
                    
                    if keyword:
                        where_conditions.append("(title LIKE %s OR content LIKE %s)")
                        params.extend([f'%{keyword}%', f'%{keyword}%'])
                    
                    where_clause = ""
                    if where_conditions:
                        where_clause = "WHERE " + " AND ".join(where_conditions)
                    
                    # 查询总数
                    count_sql = f"SELECT COUNT(*) as total FROM py_announcements {where_clause}"
                    print(f"执行SQL: {count_sql}, 参数: {params}")
                    cursor.execute(count_sql, params)
                    total = cursor.fetchone()['total']
                    
                    # 查询数据
                    offset = (page_num - 1) * page_size
                    data_sql = f"""
                        SELECT id, title, summary, content, author, authorId, status, isTop, 
                               viewCount, createTime, updateTime
                        FROM py_announcements 
                        {where_clause}
                        ORDER BY isTop DESC, createTime DESC
                        LIMIT %s OFFSET %s
                    """
                    params.extend([page_size, offset])
                    print(f"执行SQL: {data_sql}, 参数: {params}")
                    cursor.execute(data_sql, params)
                    rows = cursor.fetchall()
                    
                    return page_response(rows, total, page_num, page_size)
                    
        except Exception as e:
            print(f"获取公告列表失败: {str(e)}")
            return error(f"获取公告列表失败: {str(e)}")
    
    @staticmethod
    def get_front_announcements(page=1, limit=10, keyword='', start_date='', end_date=''):
        """
        获取前台公告列表（仅显示已发布的，支持分页和搜索）
        
        Args:
            page: 页码
            limit: 每页数量
            keyword: 关键词搜索
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            dict: 响应数据
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 构建查询条件
                    where_conditions = ["status = 1"]  # 只显示已发布的
                    params = []
                    
                    if keyword:
                        where_conditions.append("(title LIKE %s OR content LIKE %s)")
                        params.extend([f'%{keyword}%', f'%{keyword}%'])
                    
                    if start_date:
                        where_conditions.append("DATE(createTime) >= %s")
                        params.append(start_date)
                    
                    if end_date:
                        where_conditions.append("DATE(createTime) <= %s")
                        params.append(end_date)
                    
                    where_clause = "WHERE " + " AND ".join(where_conditions)
                    
                    # 查询总数
                    count_sql = f"SELECT COUNT(*) as total FROM py_announcements {where_clause}"
                    print(f"执行SQL: {count_sql}, 参数: {params}")
                    cursor.execute(count_sql, params)
                    total = cursor.fetchone()['total']
                    
                    # 查询数据
                    offset = (page - 1) * limit
                    data_sql = f"""
                        SELECT id, title, summary, content, author, createTime, isTop
                        FROM py_announcements 
                        {where_clause}
                        ORDER BY isTop DESC, createTime DESC
                        LIMIT %s OFFSET %s
                    """
                    params.extend([limit, offset])
                    print(f"执行SQL: {data_sql}, 参数: {params}")
                    cursor.execute(data_sql, params)
                    rows = cursor.fetchall()
                    
                    # 格式化时间
                    for row in rows:
                        row['createTime'] = row['createTime'] if row['createTime'] else ''
                    
                    return page_response(rows, total, page, limit)
                    
        except Exception as e:
            print(f"获取前台公告失败: {str(e)}")
            return error(f"获取前台公告失败: {str(e)}")
    
    @staticmethod
    def get_announcement_by_id(announcement_id):
        """
        根据ID获取公告详情
        
        Args:
            announcement_id: 公告ID
            
        Returns:
            dict: 响应数据
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                        SELECT id, title, summary, content, author, authorId, status, isTop, 
                               viewCount, createTime, updateTime
                        FROM py_announcements 
                        WHERE id = %s
                    """
                    print(f"执行SQL: {sql}, 参数: [{announcement_id}]")
                    cursor.execute(sql, [announcement_id])
                    row = cursor.fetchone()
                    
                    if not row:
                        return error("公告不存在")
                    
                    # 增加浏览次数
                    update_sql = "UPDATE py_announcements SET viewCount = viewCount + 1 WHERE id = %s"
                    print(f"执行SQL: {update_sql}, 参数: [{announcement_id}]")
                    cursor.execute(update_sql, [announcement_id])
                    conn.commit()
                    
                    return success(row)
                    
        except Exception as e:
            print(f"获取公告详情失败: {str(e)}")
            return error(f"获取公告详情失败: {str(e)}")
    
    @staticmethod
    def create_announcement(title, summary, content, author, author_id, status=1, is_top=0):
        """
        创建公告
        
        Args:
            title: 标题
            summary: 摘要
            content: 内容
            author: 发布人
            author_id: 发布人ID
            status: 状态（1-发布，0-草稿）
            is_top: 是否置顶（1-是，0-否）
            
        Returns:
            dict: 响应数据
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                        INSERT INTO py_announcements 
                        (title, summary, content, author, authorId, status, isTop, createTime, updateTime)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    """
                    params = [title, summary, content, author, author_id, status, is_top]
                    print(f"执行SQL: {sql}, 参数: {params}")
                    cursor.execute(sql, params)
                    conn.commit()
                    
                    announcement_id = cursor.lastrowid
                    return success({"id": announcement_id}, "公告创建成功")
                    
        except Exception as e:
            print(f"创建公告失败: {str(e)}")
            return error(f"创建公告失败: {str(e)}")
    
    @staticmethod
    def update_announcement(announcement_id, title, summary, content, author, author_id, status=1, is_top=0):
        """
        更新公告
        
        Args:
            announcement_id: 公告ID
            title: 标题
            summary: 摘要
            content: 内容
            author: 发布人
            author_id: 发布人ID
            status: 状态（1-发布，0-草稿）
            is_top: 是否置顶（1-是，0-否）
            
        Returns:
            dict: 响应数据
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查公告是否存在
                    check_sql = "SELECT id FROM py_announcements WHERE id = %s"
                    print(f"执行SQL: {check_sql}, 参数: [{announcement_id}]")
                    cursor.execute(check_sql, [announcement_id])
                    if not cursor.fetchone():
                        return error("公告不存在")
                    
                    sql = """
                        UPDATE py_announcements 
                        SET title = %s, summary = %s, content = %s, author = %s, authorId = %s, 
                            status = %s, isTop = %s, updateTime = NOW()
                        WHERE id = %s
                    """
                    params = [title, summary, content, author, author_id, status, is_top, announcement_id]
                    print(f"执行SQL: {sql}, 参数: {params}")
                    cursor.execute(sql, params)
                    conn.commit()
                    
                    return success(None, "公告更新成功")
                    
        except Exception as e:
            print(f"更新公告失败: {str(e)}")
            return error(f"更新公告失败: {str(e)}")
    
    @staticmethod
    def delete_announcement(announcement_id):
        """
        删除公告
        
        Args:
            announcement_id: 公告ID
            
        Returns:
            dict: 响应数据
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查公告是否存在
                    check_sql = "SELECT id FROM py_announcements WHERE id = %s"
                    print(f"执行SQL: {check_sql}, 参数: [{announcement_id}]")
                    cursor.execute(check_sql, [announcement_id])
                    if not cursor.fetchone():
                        return error("公告不存在")
                    
                    sql = "DELETE FROM py_announcements WHERE id = %s"
                    print(f"执行SQL: {sql}, 参数: [{announcement_id}]")
                    cursor.execute(sql, [announcement_id])
                    conn.commit()
                    
                    return success(None, "公告删除成功")
                    
        except Exception as e:
            print(f"删除公告失败: {str(e)}")
            return error(f"删除公告失败: {str(e)}")
    
    @staticmethod
    def toggle_announcement_status(announcement_id):
        """
        切换公告状态（发布/草稿）
        
        Args:
            announcement_id: 公告ID
            
        Returns:
            dict: 响应数据
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 获取当前状态
                    check_sql = "SELECT status FROM py_announcements WHERE id = %s"
                    print(f"执行SQL: {check_sql}, 参数: [{announcement_id}]")
                    cursor.execute(check_sql, [announcement_id])
                    result = cursor.fetchone()
                    
                    if not result:
                        return error("公告不存在")
                    
                    current_status = result['status']
                    new_status = 0 if current_status == 1 else 1
                    
                    # 更新状态
                    update_sql = "UPDATE py_announcements SET status = %s, updateTime = NOW() WHERE id = %s"
                    print(f"执行SQL: {update_sql}, 参数: [{new_status}, {announcement_id}]")
                    cursor.execute(update_sql, [new_status, announcement_id])
                    conn.commit()
                    
                    status_text = "发布" if new_status == 1 else "草稿"
                    return success(None, f"公告状态已切换为{status_text}")
                    
        except Exception as e:
            print(f"切换公告状态失败: {str(e)}")
            return error(f"切换公告状态失败: {str(e)}")
    
    @staticmethod
    def toggle_announcement_top(announcement_id):
        """
        切换公告置顶状态
        
        Args:
            announcement_id: 公告ID
            
        Returns:
            dict: 响应数据
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 获取当前置顶状态
                    check_sql = "SELECT isTop FROM py_announcements WHERE id = %s"
                    print(f"执行SQL: {check_sql}, 参数: [{announcement_id}]")
                    cursor.execute(check_sql, [announcement_id])
                    result = cursor.fetchone()
                    
                    if not result:
                        return error("公告不存在")
                    
                    current_top = result['isTop']
                    new_top = 0 if current_top == 1 else 1
                    
                    # 更新置顶状态
                    update_sql = "UPDATE py_announcements SET isTop = %s, updateTime = NOW() WHERE id = %s"
                    print(f"执行SQL: {update_sql}, 参数: [{new_top}, {announcement_id}]")
                    cursor.execute(update_sql, [new_top, announcement_id])
                    conn.commit()
                    
                    top_text = "置顶" if new_top == 1 else "取消置顶"
                    return success(None, f"公告已{top_text}")
                    
        except Exception as e:
            print(f"切换公告置顶状态失败: {str(e)}")
            return error(f"切换公告置顶状态失败: {str(e)}")
