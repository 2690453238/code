"""
新闻公告控制器
"""
from flask import request, session
from service.announcement_service import AnnouncementService
from utils.response import success, error


class AnnouncementController:
    """新闻公告控制器类"""
    
    @staticmethod
    def get_announcement_list():
        """
        获取公告列表（分页）
        
        Returns:
            dict: 分页响应数据
        """
        try:
            # 获取请求参数
            page_num = int(request.args.get('pageNum', 1))
            page_size = int(request.args.get('pageSize', 10))
            status = request.args.get('status')
            keyword = request.args.get('keyword')
            
            # 参数验证
            if page_num < 1:
                page_num = 1
            if page_size < 1 or page_size > 100:
                page_size = 10
            
            # 转换status参数
            if status is not None:
                try:
                    status = int(status)
                    if status not in [0, 1]:
                        status = None
                except ValueError:
                    status = None
            
            return AnnouncementService.get_announcement_list(page_num, page_size, status, keyword)
            
        except Exception as e:
            print(f"获取公告列表失败: {str(e)}")
            return error(f"获取公告列表失败: {str(e)}")
    
    @staticmethod
    def get_front_announcements():
        """
        获取前台公告列表（支持分页和搜索）
        
        Returns:
            dict: 响应数据
        """
        try:
            # 获取请求参数
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 10))
            keyword = request.args.get('keyword', '').strip()
            start_date = request.args.get('startDate', '').strip()
            end_date = request.args.get('endDate', '').strip()
            
            # 参数验证
            if page < 1:
                page = 1
            if limit < 1 or limit > 100:
                limit = 10
            
            return AnnouncementService.get_front_announcements(
                page, limit, keyword, start_date, end_date
            )
            
        except Exception as e:
            print(f"获取前台公告失败: {str(e)}")
            return error(f"获取前台公告失败: {str(e)}")
    
    @staticmethod
    def get_announcement_detail():
        """
        获取公告详情
        
        Returns:
            dict: 响应数据
        """
        try:
            announcement_id = request.args.get('id')
            if not announcement_id:
                return error("缺少公告ID参数")
            
            try:
                announcement_id = int(announcement_id)
            except ValueError:
                return error("公告ID格式错误")
            
            return AnnouncementService.get_announcement_by_id(announcement_id)
            
        except Exception as e:
            print(f"获取公告详情失败: {str(e)}")
            return error(f"获取公告详情失败: {str(e)}")
    
    @staticmethod
    def create_announcement():
        """
        创建公告
        
        Returns:
            dict: 响应数据
        """
        try:
            # 检查用户登录状态
            if 'user_id' not in session:
                return error("请先登录")
            
            # 获取请求数据
            data = request.get_json()
            if not data:
                return error("缺少请求数据")
            
            title = data.get('title', '').strip()
            summary = data.get('summary', '').strip()
            content = data.get('content', '').strip()
            status = data.get('status', 1)
            is_top = data.get('isTop', 0)
            
            # 参数验证
            if not title:
                return error("公告标题不能为空")
            if not summary:
                return error("公告摘要不能为空")
            if not content:
                return error("公告内容不能为空")
            if len(title) > 200:
                return error("公告标题不能超过200个字符")
            if len(summary) > 500:
                return error("公告摘要不能超过500个字符")
            
            # 状态验证
            if status not in [0, 1]:
                status = 1
            if is_top not in [0, 1]:
                is_top = 0
            
            # 获取用户信息
            user_id = session['user_id']
            username = session.get('username', '未知用户')
            
            return AnnouncementService.create_announcement(
                title, summary, content, username, user_id, status, is_top
            )
            
        except Exception as e:
            print(f"创建公告失败: {str(e)}")
            return error(f"创建公告失败: {str(e)}")
    
    @staticmethod
    def update_announcement():
        """
        更新公告
        
        Returns:
            dict: 响应数据
        """
        try:
            # 检查用户登录状态
            if 'user_id' not in session:
                return error("请先登录")
            
            # 获取请求数据
            data = request.get_json()
            if not data:
                return error("缺少请求数据")
            
            announcement_id = data.get('id')
            if not announcement_id:
                return error("缺少公告ID")
            
            try:
                announcement_id = int(announcement_id)
            except ValueError:
                return error("公告ID格式错误")
            
            title = data.get('title', '').strip()
            summary = data.get('summary', '').strip()
            content = data.get('content', '').strip()
            status = data.get('status', 1)
            is_top = data.get('isTop', 0)
            
            # 参数验证
            if not title:
                return error("公告标题不能为空")
            if not summary:
                return error("公告摘要不能为空")
            if not content:
                return error("公告内容不能为空")
            if len(title) > 200:
                return error("公告标题不能超过200个字符")
            if len(summary) > 500:
                return error("公告摘要不能超过500个字符")
            
            # 状态验证
            if status not in [0, 1]:
                status = 1
            if is_top not in [0, 1]:
                is_top = 0
            
            # 获取用户信息
            user_id = session['user_id']
            username = session.get('username', '未知用户')
            
            return AnnouncementService.update_announcement(
                announcement_id, title, summary, content, username, user_id, status, is_top
            )
            
        except Exception as e:
            print(f"更新公告失败: {str(e)}")
            return error(f"更新公告失败: {str(e)}")
    
    @staticmethod
    def delete_announcement():
        """
        删除公告
        
        Returns:
            dict: 响应数据
        """
        try:
            # 检查用户登录状态
            if 'user_id' not in session:
                return error("请先登录")
            
            announcement_id = request.args.get('id')
            if not announcement_id:
                return error("缺少公告ID参数")
            
            try:
                announcement_id = int(announcement_id)
            except ValueError:
                return error("公告ID格式错误")
            
            return AnnouncementService.delete_announcement(announcement_id)
            
        except Exception as e:
            print(f"删除公告失败: {str(e)}")
            return error(f"删除公告失败: {str(e)}")
    
    @staticmethod
    def toggle_announcement_status():
        """
        切换公告状态
        
        Returns:
            dict: 响应数据
        """
        try:
            # 检查用户登录状态
            if 'user_id' not in session:
                return error("请先登录")
            
            announcement_id = request.args.get('id')
            if not announcement_id:
                return error("缺少公告ID参数")
            
            try:
                announcement_id = int(announcement_id)
            except ValueError:
                return error("公告ID格式错误")
            
            return AnnouncementService.toggle_announcement_status(announcement_id)
            
        except Exception as e:
            print(f"切换公告状态失败: {str(e)}")
            return error(f"切换公告状态失败: {str(e)}")
    
    @staticmethod
    def toggle_announcement_top():
        """
        切换公告置顶状态
        
        Returns:
            dict: 响应数据
        """
        try:
            # 检查用户登录状态
            if 'user_id' not in session:
                return error("请先登录")
            
            announcement_id = request.args.get('id')
            if not announcement_id:
                return error("缺少公告ID参数")
            
            try:
                announcement_id = int(announcement_id)
            except ValueError:
                return error("公告ID格式错误")
            
            return AnnouncementService.toggle_announcement_top(announcement_id)
            
        except Exception as e:
            print(f"切换公告置顶状态失败: {str(e)}")
            return error(f"切换公告置顶状态失败: {str(e)}")
