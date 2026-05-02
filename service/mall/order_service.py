"""
订单管理服务
"""
from utils.db_utils import get_db_connection
from utils.response import success, error, page_response
import pymysql
import uuid
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation


class OrderService:
    @staticmethod
    def _build_supplier_filter(supplier_id):
        """构建社区订单过滤条件"""
        if supplier_id is None:
            return "", []
        return " AND supplierId = %s", [supplier_id]

    @staticmethod
    def _resolve_order_supplier_id(cursor, items):
        """解析订单所属社区团长"""
        supplier_ids = set()
        for item in items:
            product_id = item.get('productId')
            if not product_id:
                return None, error('订单商品参数错误')

            cursor.execute(
                "SELECT supplierId FROM py_product WHERE id = %s LIMIT 1",
                (product_id,)
            )
            product = cursor.fetchone()
            if not product:
                return None, error('订单商品不存在')
            supplier_ids.add(product.get('supplierId'))

        if len(supplier_ids) > 1:
            return None, error('同一订单仅支持提交同一社区商品')

        return supplier_ids.pop() if supplier_ids else None, None
    """订单管理服务类"""
    
    def get_orders_by_user(self, user_id, page=1, limit=10, status=''):
        """获取用户订单列表"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 构建查询条件
                    where_conditions = ["userId = %s"]
                    params = [user_id]
                    
                    if status:
                        where_conditions.append("status = %s")
                        params.append(status)
                    
                    where_clause = " AND ".join(where_conditions)
                    
                    # 查询总数
                    count_sql = f"SELECT COUNT(*) as total FROM py_order WHERE {where_clause}"
                    print(f"执行SQL: {count_sql}, 参数: {params}")
                    cursor.execute(count_sql, params)
                    total = cursor.fetchone()['total']
                    
                    # 查询订单列表
                    offset = (page - 1) * limit
                    sql = f"""
                        SELECT id, orderNo, status, payAmount, 
                               payMethod, createTime, updateTime
                        FROM py_order 
                        WHERE {where_clause}
                        ORDER BY createTime DESC
                        LIMIT %s OFFSET %s
                    """
                    params.extend([limit, offset])
                    print(f"执行SQL: {sql}, 参数: {params}")
                    cursor.execute(sql, params)
                    orders = cursor.fetchall()
                    
                    # 获取每个订单的商品信息
                    formatted_orders = []
                    for order in orders:
                        # 获取订单商品
                        items_sql = """
                            SELECT oi.id, oi.productId, oi.skuId, oi.productName, oi.skuName,
                                   oi.productImage, oi.price, oi.quantity, oi.reviewContent, oi.reviewRating, oi.reviewTime
                            FROM py_order_item oi
                            WHERE oi.orderId = %s
                        """
                        cursor.execute(items_sql, (order['id'],))
                        items = cursor.fetchall()
                        
                        formatted_order = {
                            'id': order['id'],
                            'orderNo': order['orderNo'],
                            'status': order['status'],
                            'payAmount': float(order['payAmount']),
                            'payMethod': order['payMethod'],
                            'createTime': order['createTime'] if order['createTime'] else '',
                            'updateTime': order['updateTime'] if order['updateTime'] else '',
                            'items': []
                        }
                        
                        for item in items:
                            formatted_order['items'].append({
                                'id': item['id'],
                                'productId': item['productId'],
                                'skuId': item['skuId'],
                                'productName': item['productName'],
                                'skuName': item['skuName'],
                                'productImage': item['productImage'],
                                'price': float(item['price']),
                                'quantity': item['quantity'],
                                'reviewContent': item['reviewContent'],
                                'reviewRating': item['reviewRating'],
                                'reviewTime': item['reviewTime'],
                                'isReviewed': item['reviewContent'] is not None
                            })
                        
                        formatted_orders.append(formatted_order)
                    
                    return page_response(formatted_orders, total, page, limit)
        except Exception as e:
            print(f"获取订单列表失败: {e}")
            return error(f"获取订单列表失败: {str(e)}")
    
    def create_order(self, user_id, data):
        """创建订单"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 生成订单号
                    order_number = self._generate_order_number()
                    supplier_id, supplier_error = self._resolve_order_supplier_id(cursor, data['items'])
                    if supplier_error:
                        return supplier_error
                    
                    # 检查库存和社区归属
                    for item in data['items']:
                        product_id = item.get('productId')
                        quantity = int(item.get('quantity', 0))
                        cursor.execute(
                            "SELECT id, name, stock, supplierId FROM py_product WHERE id = %s LIMIT 1",
                            (product_id,)
                        )
                        product = cursor.fetchone()
                        if not product:
                            return error(f'商品不存在: {item.get("productName", "")}')
                        if product['stock'] < quantity:
                            return error(f'商品 [{product["name"]}] 库存不足，仅剩 {product["stock"]} 件')
                        if supplier_id is not None and product['supplierId'] != supplier_id:
                            return error(f'商品 [{product["name"]}] 不属于当前社区，无法购买')

                    # 计算订单总金额
                    total_amount = Decimal('0')
                    for item in data['items']:
                        try:
                            price = Decimal(str(item.get('price', '0')))
                            quantity = int(item.get('quantity', 0))
                            total_amount += price * quantity
                        except (InvalidOperation, ValueError, TypeError):
                            continue
                    
                    # 创建订单记录
                    order_sql = """
                        INSERT INTO py_order 
                        (supplierId, orderNo, userId, status, totalAmount, payAmount, payMethod,
                         receiverName, receiverPhone, receiverProvince, receiverCity,
                         receiverDistrict, receiverAddress, createTime)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    # 获取收货地址信息
                    address_sql = "SELECT * FROM py_address WHERE id = %s AND userId = %s"
                    cursor.execute(address_sql, (data['addressId'], user_id))
                    address = cursor.fetchone()
                    
                    if not address:
                        return error('收货地址不存在')
                    
                    order_values = (
                        supplier_id,
                        order_number,
                        user_id,
                        'pending',
                        total_amount,
                        total_amount,  # 暂时payAmount等于totalAmount
                        data.get('paymentMethod', 'alipay'),
                        address['name'],
                        address['phone'],
                        address['province'],
                        address['city'],
                        address['district'],
                        address['address'],
                        time.strftime('%Y-%m-%d %H:%M:%S')
                    )
                    
                    print(f"执行SQL: {order_sql}, 参数: {order_values}")
                    cursor.execute(order_sql, order_values)
                    order_id = cursor.lastrowid
                    
                    # 创建订单商品
                    for item in data['items']:
                        item_sql = """
                            INSERT INTO py_order_item 
                            (orderId, productId, skuId, productName, skuName, 
                             productImage, price, quantity, totalAmount)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        try:
                            item_price = Decimal(str(item.get('price', '0')))
                            item_quantity = int(item.get('quantity', 0))
                        except (InvalidOperation, ValueError, TypeError):
                            item_price = Decimal('0')
                            item_quantity = 0
                        
                        item_total = item_price * item_quantity
                        
                        item_values = (
                            order_id,
                            item['productId'],
                            item.get('skuId'),
                            item['productName'],
                            item.get('skuName', ''),
                            item.get('productImage', ''),
                            item_price,
                            item_quantity,
                            item_total
                        )
                        
                        print(f"执行SQL: {item_sql}, 参数: {item_values}")
                        cursor.execute(item_sql, item_values)
                    
                    # 删除购物车中已结算的商品
                    print(f"订单商品数据: {data['items']}")
                    
                    # 根据用户ID和商品ID删除购物车中的商品
                    for item in data['items']:
                        product_id = item.get('productId')
                        sku_id = item.get('skuId')
                        
                        if sku_id:
                            # 如果有规格，根据用户ID、商品ID和规格ID删除
                            cart_delete_sql = """
                                DELETE FROM py_cart 
                                WHERE userId = %s AND productId = %s AND skuId = %s
                            """
                            print(f"执行SQL: {cart_delete_sql}, 参数: {user_id}, {product_id}, {sku_id}")
                            cursor.execute(cart_delete_sql, (user_id, product_id, sku_id))
                        else:
                            # 如果没有规格，根据用户ID和商品ID删除
                            cart_delete_sql = """
                                DELETE FROM py_cart 
                                WHERE userId = %s AND productId = %s AND skuId IS NULL
                            """
                            print(f"执行SQL: {cart_delete_sql}, 参数: {user_id}, {product_id}")
                            cursor.execute(cart_delete_sql, (user_id, product_id))
                        
                        deleted_count = cursor.rowcount
                        print(f"删除购物车商品成功，影响行数: {deleted_count}")

                    # 扣减库存
                    for item in data['items']:
                        product_id = item.get('productId')
                        quantity = int(item.get('quantity', 0))
                        cursor.execute(
                            "UPDATE py_product SET stock = stock - %s WHERE id = %s AND stock >= %s",
                            (quantity, product_id, quantity)
                        )
                        if cursor.rowcount == 0:
                            conn.rollback()
                            return error(f'商品 [{item.get("productName", "")}] 库存扣减失败，请重试')

                    conn.commit()

                    return success({'orderId': order_id, 'orderNo': order_number}, '订单创建成功')
        except Exception as e:
            print(f"创建订单失败: {e}")
            return error(f"创建订单失败: {str(e)}")

    def get_order_by_id(self, order_id, user_id=None, supplier_id=None):
        """获取订单详情"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 获取订单基本信息
                    if user_id is not None:
                        # 普通用户查询，需要验证用户ID
                        order_sql = """
                            SELECT id, orderNo, status, totalAmount, payAmount, 
                                   payMethod, receiverName, receiverPhone, receiverProvince, 
                                   receiverCity, receiverDistrict, receiverAddress, createTime, updateTime,
                                   trackingNumber, shippingCompany, shippingTime, shippingStatus,
                                   deliveryTime, logisticsInfo
                            FROM py_order 
                            WHERE id = %s AND userId = %s
                        """
                        print(f"执行SQL: {order_sql}, 参数: {order_id}, {user_id}")
                        cursor.execute(order_sql, (order_id, user_id))
                    elif supplier_id is not None:
                        order_sql = """
                            SELECT id, orderNo, status, totalAmount, payAmount, 
                                   payMethod, receiverName, receiverPhone, receiverProvince, 
                                   receiverCity, receiverDistrict, receiverAddress, createTime, updateTime,
                                   trackingNumber, shippingCompany, shippingTime, shippingStatus,
                                   deliveryTime, logisticsInfo
                            FROM py_order 
                            WHERE id = %s AND supplierId = %s
                        """
                        print(f"鎵цSQL: {order_sql}, 鍙傛暟: {order_id}, {supplier_id}")
                        cursor.execute(order_sql, (order_id, supplier_id))
                    else:
                        # 管理员查询，不需要验证用户ID
                        order_sql = """
                            SELECT id, orderNo, status, totalAmount, payAmount, 
                                   payMethod, receiverName, receiverPhone, receiverProvince, 
                                   receiverCity, receiverDistrict, receiverAddress, createTime, updateTime,
                                   trackingNumber, shippingCompany, shippingTime, shippingStatus,
                                   deliveryTime, logisticsInfo
                            FROM py_order 
                            WHERE id = %s
                        """
                        print(f"执行SQL: {order_sql}, 参数: {order_id}")
                        cursor.execute(order_sql, (order_id,))
                    order = cursor.fetchone()

                    if not order:
                        return error('订单不存在')
                    
                    # 获取订单商品
                    items_sql = """
                        SELECT id, productId, skuId, productName, skuName,
                               productImage, price, quantity, reviewContent, reviewRating, reviewTime
                        FROM py_order_item
                        WHERE orderId = %s
                    """
                    cursor.execute(items_sql, (order_id,))
                    items = cursor.fetchall()

                    # 计算运费（假设运费为0，或者通过totalAmount - payAmount计算）
                    shipping_fee = 0.0  # 暂时设为0，实际项目中可能需要单独计算运费
                    
                    # 地址信息已包含在订单表中
                    formatted_order = {
                        'id': order['id'],
                        'orderNo': order['orderNo'],
                        'status': order['status'],
                        'totalAmount': float(order['totalAmount']),
                        'payAmount': float(order['payAmount']),
                        'shippingFee': shipping_fee,
                        'paymentMethod': order['payMethod'],  # 修复字段名称
                        'createTime': order['createTime'] if order['createTime'] else '',
                        'updateTime': order['updateTime'] if order['updateTime'] else '',
                        'receiverName': order['receiverName'],
                        'receiverPhone': order['receiverPhone'],
                        'receiverProvince': order['receiverProvince'],
                        'receiverCity': order['receiverCity'],
                        'receiverDistrict': order['receiverDistrict'],
                        'receiverAddress': order['receiverAddress'],
                        'address': {
                            'name': order['receiverName'],
                            'phone': order['receiverPhone'],
                            'address': f"{order['receiverProvince']} {order['receiverCity']} {order['receiverDistrict']} {order['receiverAddress']}"
                        },
                        'trackingNumber': order['trackingNumber'] if order['trackingNumber'] else '',
                        'shippingCompany': order['shippingCompany'] if order['shippingCompany'] else '',
                        'shippingTime': order['shippingTime'] if order['shippingTime'] else '',
                        'logisticsInfo': order['logisticsInfo'] if order['logisticsInfo'] else '',
                        'items': []
                    }
                    
                    # 如果订单已发货，添加物流信息
                    if order['status'] in ['shipped', 'delivered', 'completed']:
                        formatted_order['shippingInfo'] = {
                            'trackingNumber': order['trackingNumber'] if order['trackingNumber'] else '',
                            'shippingCompany': order['shippingCompany'] if order['shippingCompany'] else '',
                            'shippingTime': order['shippingTime'] if order['shippingTime'] else '',
                            'shippingStatus': order['shippingStatus'] if order['shippingStatus'] else '',
                            'deliveryTime': order['deliveryTime'] if order['deliveryTime'] else ''
                        }
                    
                    for item in items:
                        formatted_order['items'].append({
                            'id': item['id'],
                            'productId': item['productId'],
                            'skuId': item['skuId'],
                            'productName': item['productName'],
                            'skuName': item['skuName'],
                            'image': item['productImage'],  # 修复字段名称
                            'price': float(item['price']),
                            'quantity': item['quantity'],
                            'reviewContent': item['reviewContent'],
                            'reviewRating': item['reviewRating'],
                            'reviewTime': item['reviewTime'],
                            'isReviewed': item['reviewContent'] is not None
                        })
                    
                    return success(formatted_order)
        except Exception as e:
            print(f"获取订单详情失败: {e}")
            return error(f"获取订单详情失败: {str(e)}")

    def pay_order(self, order_id, user_id, payment_method):
        """支付订单"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查订单状态
                    check_sql = "SELECT status FROM py_order WHERE id = %s AND userId = %s"
                    cursor.execute(check_sql, (order_id, user_id))
                    order = cursor.fetchone()

                    if not order:
                        return error('订单不存在')

                    if order['status'] != 'pending':
                        return error('订单状态不正确，无法支付')

                    # 更新订单状态为已付款
                    reply_content = ''
                    try:
                        from flask import request as _request
                        payload = _request.get_json(silent=True) or {}
                        reply_content = (payload.get('replyContent') or '').strip()
                    except Exception:
                        reply_content = ''

                    final_remark = order.get('remark') or ''
                    if reply_content:
                        reply_line = f"售后处理回复：{reply_content}"
                        final_remark = f"{final_remark}\n{reply_line}".strip() if final_remark else reply_line

                    update_sql = """
                        UPDATE py_order 
                        SET status = 'paid', payMethod = %s, updateTime = NOW()
                        WHERE id = %s AND userId = %s
                    """
                    print(f"执行SQL: {update_sql}, 参数: {payment_method}, {order_id}, {user_id}")
                    cursor.execute(update_sql, (payment_method, order_id, user_id))
                    
                    # 注意：购物车商品已在订单创建时删除，支付时无需再次删除
                    print("订单支付成功，购物车商品已在订单创建时删除")
                    
                    conn.commit()

                    return success(None, '支付成功')
        except Exception as e:
            print(f"支付订单失败: {e}")
            return error(f"支付订单失败: {str(e)}")

    def confirm_receive(self, order_id, user_id):
        """确认收货"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查订单状态
                    check_sql = "SELECT status FROM py_order WHERE id = %s AND userId = %s"
                    cursor.execute(check_sql, (order_id, user_id))
                    order = cursor.fetchone()

                    if not order:
                        return error('订单不存在')

                    if order['status'] != 'shipped':
                        return error('订单状态不正确，无法确认收货')

                    # 更新订单状态为已完成
                    update_sql = """
                        UPDATE py_order 
                        SET status = 'completed', updateTime = NOW()
                        WHERE id = %s AND userId = %s
                    """
                    print(f"执行SQL: {update_sql}, 参数: {order_id}, {user_id}")
                    cursor.execute(update_sql, (order_id, user_id))
                    conn.commit()

                    return success(None, '确认收货成功')
        except Exception as e:
            print(f"确认收货失败: {e}")
            return error(f"确认收货失败: {str(e)}")
    
    def cancel_order(self, order_id, user_id):
        """提交取消订单申请"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查订单状态
                    check_sql = "SELECT status FROM py_order WHERE id = %s AND userId = %s"
                    cursor.execute(check_sql, (order_id, user_id))
                    order = cursor.fetchone()

                    if not order:
                        return error('订单不存在')

                    if order['status'] not in ['pending', 'paid']:
                        return error('订单状态不正确，无法提交取消申请')

                    # 更新订单状态为取消申请中
                    update_sql = """
                        UPDATE py_order 
                        SET status = 'cancel_requested', updateTime = NOW()
                        WHERE id = %s AND userId = %s
                    """
                    print(f"执行SQL: {update_sql}, 参数: {order_id}, {user_id}")
                    cursor.execute(update_sql, (order_id, user_id))
                    conn.commit()

                    return success(None, '取消申请已提交，请等待审核')
        except Exception as e:
            print(f"提交取消申请失败: {e}")
            return error(f"提交取消申请失败: {str(e)}")
    
    def get_order_stats(self, user_id):
        """获取订单统计"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    supplier_filter, supplier_params = self._build_supplier_filter(supplier_id)
                    sql = f"""
                        SELECT 
                            COUNT(*) as total,
                            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                            SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) as paid,
                            SUM(CASE WHEN status = 'shipped' THEN 1 ELSE 0 END) as shipped,
                            SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) as delivered,
                            SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled
                        FROM py_order 
                        WHERE userId = %s
                    """
                    print(f"执行SQL: {sql}, 参数: {user_id}")
                    cursor.execute(sql, (user_id,))
                    stats = cursor.fetchone()

                    return success({
                        'total': stats['total'],
                        'pending': stats['pending'],
                        'paid': stats['paid'],
                        'shipped': stats['shipped'],
                        'delivered': stats['delivered'],
                        'cancelled': stats['cancelled']
                    })
        except Exception as e:
            print(f"获取订单统计失败: {e}")
            return error(f"获取订单统计失败: {str(e)}")
    
    def _generate_order_number(self):
        """生成订单号"""
        timestamp = str(int(time.time()))
        random_str = str(uuid.uuid4()).replace('-', '')[:8]
        return f"ORD{timestamp}{random_str}".upper()
    
    def admin_approve_cancel(self, order_id, approve=True, supplier_id=None):
        """管理员审核取消申请"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查订单状态
                    check_sql = "SELECT status, supplierId, remark FROM py_order WHERE id = %s"
                    cursor.execute(check_sql, (order_id,))
                    order = cursor.fetchone()

                    if not order:
                        return error('订单不存在')

                    if supplier_id is not None and order.get('supplierId') != supplier_id:
                        return error('鏃犳潈闄愬鐞嗚鍞悗璁㈠崟')

                    if order['status'] != 'cancel_requested':
                        return error('订单状态不正确，无法审核')

                    # 根据审核结果更新订单状态
                    final_remark = order.get('remark') or ''
                    if approve:
                        new_status = 'cancelled'
                        message = '取消申请已通过'
                    else:
                        # 根据原订单状态恢复
                        new_status = 'paid'  # 假设原状态是已付款
                        message = '取消申请已拒绝'

                    action_text = '审核结果：取消申请已通过' if approve else '审核结果：取消申请已拒绝'
                    final_remark = f"{final_remark}\n{action_text}".strip() if final_remark else action_text

                    update_sql = """
                        UPDATE py_order 
                        SET status = %s, remark = %s, updateTime = NOW()
                        WHERE id = %s
                    """
                    print(f"执行SQL: {update_sql}, 参数: {new_status}, {order_id}")
                    cursor.execute(update_sql, (new_status, final_remark, order_id))
                    conn.commit()

                    return success(None, message)
        except Exception as e:
            print(f"审核取消申请失败: {e}")
            return error(f"审核取消申请失败: {str(e)}")
    
    def get_orders_admin(self, page=1, limit=10, order_no='', username='', status='', start_time='', end_time='', supplier_id=None):
        """管理员获取订单列表"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 构建查询条件
                    where_conditions = []
                    params = []
                    
                    if order_no:
                        where_conditions.append("o.orderNo LIKE %s")
                        params.append(f'%{order_no}%')
                    
                    if username:
                        where_conditions.append("u.username LIKE %s")
                        params.append(f'%{username}%')
                    
                    if status:
                        where_conditions.append("o.status = %s")
                        params.append(status)
                    
                    if start_time:
                        where_conditions.append("o.createTime >= %s")
                        params.append(start_time)
                    
                    if end_time:
                        where_conditions.append("o.createTime <= %s")
                        params.append(end_time)

                    if supplier_id is not None:
                        where_conditions.append("o.supplierId = %s")
                        params.append(supplier_id)
                    
                    where_clause = ""
                    if where_conditions:
                        where_clause = "WHERE " + " AND ".join(where_conditions)
                    
                    # 查询总数
                    count_sql = f"""
                        SELECT COUNT(*) as total 
                        FROM py_order o
                        LEFT JOIN py_user u ON o.userId = u.id
                        {where_clause}
                    """
                    print(f"执行SQL: {count_sql}, 参数: {params}")
                    cursor.execute(count_sql, params)
                    total = cursor.fetchone()['total']
                    
                    # 查询订单列表
                    offset = (page - 1) * limit
                    sql = f"""
                        SELECT o.id, o.orderNo, o.status, o.totalAmount, o.payAmount,
                               o.payMethod, o.receiverName, o.receiverPhone, 
                               o.createTime, o.updateTime, o.trackingNumber, o.shippingCompany,
                               u.username, u.phone
                        FROM py_order o
                        LEFT JOIN py_user u ON o.userId = u.id
                        {where_clause}
                        ORDER BY o.createTime DESC
                        LIMIT %s OFFSET %s
                    """
                    params.extend([limit, offset])
                    print(f"执行SQL: {sql}, 参数: {params}")
                    cursor.execute(sql, params)
                    orders = cursor.fetchall()
                    
                    # 获取每个订单的商品信息
                    formatted_orders = []
                    for order in orders:
                        # 获取订单商品
                        items_sql = """
                            SELECT oi.id, oi.productId, oi.skuId, oi.productName, oi.skuName,
                                   oi.productImage, oi.price, oi.quantity, oi.reviewContent, 
                                   oi.reviewRating, oi.reviewTime
                            FROM py_order_item oi
                            WHERE oi.orderId = %s
                        """
                        cursor.execute(items_sql, (order['id'],))
                        items = cursor.fetchall()
                        
                        formatted_order = {
                            'id': order['id'],
                            'orderNo': order['orderNo'],
                            'status': order['status'],
                            'totalAmount': float(order['totalAmount']),
                            'payAmount': float(order['payAmount']),
                            'payMethod': order['payMethod'],
                            'receiverName': order['receiverName'],
                            'receiverPhone': order['receiverPhone'],
                            'createTime': order['createTime'] if order['createTime'] else '',
                            'updateTime': order['updateTime'] if order['updateTime'] else '',
                            'username': order['username'],
                            'phone': order['phone'],
                            'items': []
                        }
                        
                        for item in items:
                            formatted_order['items'].append({
                                'id': item['id'],
                                'productId': item['productId'],
                                'skuId': item['skuId'],
                                'productName': item['productName'],
                                'skuName': item['skuName'],
                                'productImage': item['productImage'],
                                'price': float(item['price']),
                                'quantity': item['quantity'],
                                'reviewContent': item['reviewContent'],
                                'reviewRating': item['reviewRating'],
                                'reviewTime': item['reviewTime'],
                                'isReviewed': item['reviewContent'] is not None
                            })
                        
                        formatted_orders.append(formatted_order)
                    
                    return page_response(formatted_orders, total, page, limit)
        except Exception as e:
            print(f"管理员获取订单列表失败: {e}")
            return error(f"管理员获取订单列表失败: {str(e)}")
    
    def get_cancel_requests(self, supplier_id=None):
        """获取所有取消申请"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    supplier_filter, supplier_params = self._build_supplier_filter(supplier_id)
                    sql = f"""
                        SELECT o.id, o.orderNo, o.status, o.totalAmount, o.payAmount,
                               o.receiverName, o.receiverPhone, o.createTime, o.updateTime,
                               u.username, u.phone
                        FROM py_order o
                        LEFT JOIN py_user u ON o.userId = u.id
                        WHERE o.status = 'cancel_requested' {supplier_filter}
                        ORDER BY o.updateTime DESC
                    """
                    print(f"执行SQL: {sql}")
                    cursor.execute(sql, supplier_params)
                    orders = cursor.fetchall()

                    return success(orders)
        except Exception as e:
            print(f"获取取消申请失败: {e}")
            return error(f"获取取消申请失败: {str(e)}")

    def review_order_item(self, order_id, item_id, user_id, rating, content):
        """评价订单商品"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查订单是否存在且属于当前用户
                    check_order_sql = "SELECT status FROM py_order WHERE id = %s AND userId = %s"
                    cursor.execute(check_order_sql, (order_id, user_id))
                    order = cursor.fetchone()

                    if not order:
                        return error('订单不存在')

                    if order['status'] != 'completed':
                        return error('只有已完成的订单才能评价')

                    # 检查订单商品是否存在且未评价
                    check_item_sql = """
                        SELECT id, reviewContent, reviewRating 
                        FROM py_order_item 
                        WHERE id = %s AND orderId = %s
                    """
                    cursor.execute(check_item_sql, (item_id, order_id))
                    item = cursor.fetchone()

                    if not item:
                        return error('订单商品不存在')

                    if item['reviewContent'] is not None:
                        return error('该商品已经评价过了')

                    # 更新评价信息
                    update_sql = """
                        UPDATE py_order_item 
                        SET reviewContent = %s, reviewRating = %s, reviewTime = NOW()
                        WHERE id = %s AND orderId = %s
                    """
                    print(f"执行SQL: {update_sql}, 参数: {content}, {rating}, {item_id}, {order_id}")
                    cursor.execute(update_sql, (content, rating, item_id, order_id))
                    conn.commit()

                    return success(None, '评价成功')
        except Exception as e:
            print(f"评价失败: {e}")
            return error(f"评价失败: {str(e)}")

    def delete_order(self, order_id, user_id):
        """删除订单"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查订单是否存在且属于当前用户
                    check_sql = """
                        SELECT id, status, userId FROM py_order 
                        WHERE id = %s AND userId = %s
                    """
                    cursor.execute(check_sql, (order_id, user_id))
                    order = cursor.fetchone()
                    
                    if not order:
                        return error('订单不存在或无权限删除')
                    
                    # 只有已取消、已完成或取消申请中的订单才能删除
                    if order['status'] not in ['cancelled', 'completed', 'cancel_requested']:
                        return error('只有已取消、已完成或取消申请中的订单才能删除')
                    
                    # 删除订单商品
                    # delete_items_sql = "DELETE FROM py_order_item WHERE orderId = %s"
                    # print(f"执行SQL: {delete_items_sql}, 参数: {order_id}")
                    # cursor.execute(delete_items_sql, (order_id,))
                    
                    # 删除订单
                    delete_order_sql = "DELETE FROM py_order WHERE id = %s"
                    print(f"执行SQL: {delete_order_sql}, 参数: {order_id}")
                    cursor.execute(delete_order_sql, (order_id,))
                    
                    conn.commit()
                    return success('订单删除成功')
                    
        except Exception as e:
            print(f"删除订单失败: {e}")
            return error('删除订单失败')

    def delete_order(self, order_id, user_id):
        """删除订单"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    check_sql = """
                        SELECT id, status FROM py_order
                        WHERE id = %s AND userId = %s
                    """
                    cursor.execute(check_sql, (order_id, user_id))
                    order = cursor.fetchone()

                    if not order:
                        return error('订单不存在或无权限删除')

                    if order['status'] not in ['cancelled', 'completed', 'cancel_requested']:
                        return error('只有已取消、已完成或取消申请中的订单才能删除')

                    delete_items_sql = "DELETE FROM py_order_item WHERE orderId = %s"
                    cursor.execute(delete_items_sql, (order_id,))

                    delete_order_sql = "DELETE FROM py_order WHERE id = %s AND userId = %s"
                    cursor.execute(delete_order_sql, (order_id, user_id))

                    if cursor.rowcount == 0:
                        conn.rollback()
                        return error('订单删除失败，请稍后重试')

                    conn.commit()
                    return success('订单删除成功')
        except Exception as e:
            print(f"删除订单失败: {e}")
            return error('删除订单失败')

    def ship_order(self, order_id, tracking_number, shipping_company='', logistics_info='', supplier_id=None):
        """发货（管理员）"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查订单是否存在且状态为已付款
                    supplier_filter, supplier_params = self._build_supplier_filter(supplier_id)
                    check_sql = f"""
                        SELECT id, status FROM py_order 
                        WHERE id = %s {supplier_filter}
                    """
                    cursor.execute(check_sql, [order_id] + supplier_params)
                    order = cursor.fetchone()
                    
                    if not order:
                        return error('订单不存在')
                    
                    if order['status'] != 'paid':
                        return error('只有已付款的订单才能发货')
                    
                    # 更新订单状态为已发货
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    update_sql = """
                        UPDATE py_order 
                        SET status = 'shipped', 
                            shippingStatus = 'shipped',
                            shippingTime = %s,
                            trackingNumber = %s,
                            shippingCompany = %s,
                            logisticsInfo = %s,
                            updateTime = %s
                        WHERE id = %s
                    """
                    print(f"执行SQL: {update_sql}")
                    print(f"参数: {current_time}, {tracking_number}, {shipping_company}, {logistics_info}, {current_time}, {order_id}")
                    cursor.execute(update_sql, (current_time, tracking_number, shipping_company, logistics_info, current_time, order_id))
                    
                    conn.commit()
                    return success('发货成功')
                    
        except Exception as e:
            print(f"发货失败: {e}")
            return error(f"发货失败: {str(e)}")

    def complete_order(self, order_id, supplier_id=None):
        """完成订单（管理员）"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查订单是否存在且状态为已发货
                    supplier_filter, supplier_params = self._build_supplier_filter(supplier_id)
                    check_sql = f"""
                        SELECT id, status FROM py_order 
                        WHERE id = %s {supplier_filter}
                    """
                    cursor.execute(check_sql, [order_id] + supplier_params)
                    order = cursor.fetchone()
                    
                    if not order:
                        return error('订单不存在')
                    
                    if order['status'] != 'shipped':
                        return error('只有已发货的订单才能完成')
                    
                    # 更新订单状态为已完成
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    update_sql = """
                        UPDATE py_order 
                        SET status = 'completed', 
                            shippingStatus = 'delivered',
                            deliveryTime = %s,
                            updateTime = %s
                        WHERE id = %s
                    """
                    print(f"执行SQL: {update_sql}")
                    print(f"参数: {current_time}, {current_time}, {order_id}")
                    cursor.execute(update_sql, (current_time, current_time, order_id))
                    
                    conn.commit()
                    return success('订单完成成功')
                    
        except Exception as e:
            print(f"完成订单失败: {e}")
            return error(f"完成订单失败: {str(e)}")

    def update_logistics_info(self, order_id, logistics_info, supplier_id=None):
        """更新物流信息（管理员）"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查订单是否存在
                    supplier_filter, supplier_params = self._build_supplier_filter(supplier_id)
                    check_sql = f"""
                        SELECT id, status FROM py_order 
                        WHERE id = %s {supplier_filter}
                    """
                    cursor.execute(check_sql, [order_id] + supplier_params)
                    order = cursor.fetchone()
                    
                    if not order:
                        return error('订单不存在')
                    
                    # 更新物流信息
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    update_sql = """
                        UPDATE py_order 
                        SET logisticsInfo = %s,
                            updateTime = %s
                        WHERE id = %s
                    """
                    print(f"执行SQL: {update_sql}")
                    print(f"参数: {logistics_info}, {current_time}, {order_id}")
                    cursor.execute(update_sql, (logistics_info, current_time, order_id))
                    
                    conn.commit()
                    return success('物流信息更新成功')
                    
        except Exception as e:
            print(f"更新物流信息失败: {e}")
            return error(f"更新物流信息失败: {str(e)}")
