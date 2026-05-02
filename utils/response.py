def success(data=None, message="OK"):
    """成功响应 - 非分页接口"""
    return {
        "code": 200,
        "message": message,
        "data": data
    }

def error(message="Error", code=400):
    """错误响应"""
    return {
        "code": code,
        "message": message,
        "data": None
    }

def page_response(rows, total, page, limit):
    """分页响应 - 分页接口"""
    return {
        "code": 200,
        "message": "OK",
        "data": {
            "total": total,
            "page": page,
            "limit": limit,
            "rows": rows
        }
    }

def convert_pagination_params(request_args):
    """转换分页参数：将前端的pageNum/pageSize转换为后端的page/limit"""
    page = int(request_args.get('pageNum', 1))
    limit = int(request_args.get('pageSize', 10))
    return page, limit

# 兼容旧版本的分页响应格式
def page_response_legacy(list_data, total, page_num, page_size):
    """分页响应（兼容旧版本）"""
    return {
        "code": 200,
        "message": "OK",
        "data": {
            "total": total,
            "pageSize": page_size,
            "pageNum": page_num,
            "list": list_data
        }
    }