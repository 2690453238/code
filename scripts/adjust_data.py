"""数据调整脚本：让商品和订单数据更贴近实际社区团购"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
import random
from datetime import datetime, timedelta
from config.config import DB_CONFIG

random.seed(42)

conn = pymysql.connect(
    host=DB_CONFIG['host'],
    port=DB_CONFIG['port'],
    user=DB_CONFIG['user'],
    password=DB_CONFIG['password'],
    database=DB_CONFIG['database'],
    charset=DB_CONFIG['charset'],
    cursorclass=pymysql.cursors.DictCursor
)
cursor = conn.cursor()

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

log("开始调整数据...")

# ============================================================
# 1. 给薄订单添加更多商品项
# ============================================================
log("\n=== 1. 补充订单商品项 ===")

cursor.execute("""
    SELECT o.id, o.supplierId, MIN(oi.productId) as productId,
           MIN(oi.quantity) as quantity, MIN(oi.price) as price,
           o.totalAmount, o.payAmount
    FROM py_order o
    JOIN py_order_item oi ON oi.orderId = o.id
    WHERE o.id BETWEEN 222 AND 341
    GROUP BY o.id
    HAVING COUNT(oi.id) = 1
    ORDER BY o.id
""")
thin_orders = cursor.fetchall()
log(f"发现 {len(thin_orders)} 个单商品订单需要补充")

# For each thin order, get candidate products from the same supplier
cursor.execute("SELECT id, price, name FROM py_product WHERE status = 1")
all_products = cursor.fetchall()
products_by_supplier = {}
for p in all_products:
    cursor.execute("SELECT supplierId FROM py_product WHERE id = %s", (p['id'],))
    s = cursor.fetchone()
    sid = s['supplierId'] if s else None
    if sid not in products_by_supplier:
        products_by_supplier[sid] = []
    products_by_supplier[sid].append(p)

new_items_count = 0
updated_orders = 0

for o in thin_orders:
    order_id = o['id']
    supplier_id = o['supplierId']
    existing_product_id = o['productId']

    candidates = products_by_supplier.get(supplier_id, [])
    candidates = [c for c in candidates if c['id'] != existing_product_id]
    if len(candidates) < 2:
        continue

    # Pick 2-5 additional items
    num_extra = random.randint(2, 5)
    selected = random.sample(candidates, min(num_extra, len(candidates)))

    total_extra = 0
    items_added = 0
    for p in selected:
        qty = random.choices([1, 2, 3], weights=[4, 3, 1])[0]
        item_total = round(p['price'] * qty, 2)
        total_extra += item_total

        cursor.execute(
            """INSERT INTO py_order_item
               (orderId, productId, productName, price, quantity, totalAmount)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (order_id, p['id'], p['name'], p['price'], qty, item_total)
        )
        items_added += 1

    if items_added > 0:
        new_items_count += items_added
        # Update order total
        new_total = round(o['totalAmount'] + total_extra, 2)
        new_pay = round(o['payAmount'] + total_extra, 2)
        cursor.execute(
            "UPDATE py_order SET totalAmount = %s, payAmount = %s WHERE id = %s",
            (new_total, new_pay, order_id)
        )
        updated_orders += 1

conn.commit()
log(f"新增 {new_items_count} 个订单商品项，更新 {updated_orders} 个订单金额")

# ============================================================
# 2. 更新商品销量（基于实际订单数据）
# ============================================================
log("\n=== 2. 更新商品销量 ===")

cursor.execute("""
    SELECT oi.productId, SUM(oi.quantity) as total_qty
    FROM py_order_item oi
    JOIN py_order o ON oi.orderId = o.id
    WHERE o.status = 'completed'
    GROUP BY oi.productId
""")
sales_data = cursor.fetchall()

for s in sales_data:
    cursor.execute(
        "UPDATE py_product SET sales = %s WHERE id = %s AND sales < %s",
        (s['total_qty'], s['productId'], s['total_qty'])
    )
log(f"已更新 {len(sales_data)} 个商品的销量数据")

# ============================================================
# 3. 调整商品库存为更合理的值
# ============================================================
log("\n=== 3. 调整商品库存 ===")

cursor.execute("SELECT id, name, stock, sales, price FROM py_product WHERE status = 1")
prods = cursor.fetchall()

for p in prods:
    daily_sales = max(p['sales'] / 60.0, 0.1)  # ~2 months of data

    if p['price'] >= 50:
        # 粮油等高价耐储品 — 库存充足
        new_stock = int(daily_sales * random.randint(45, 90))
    elif p['price'] >= 20:
        # 肉禽蛋奶等 — 中等库存
        new_stock = int(daily_sales * random.randint(14, 30))
    elif p['price'] >= 10:
        # 蔬菜水果 — 周转快，库存较少
        new_stock = int(daily_sales * random.randint(5, 14))
    else:
        # 低价叶菜等 — 库存很少，快周转
        new_stock = int(daily_sales * random.randint(3, 7))

    new_stock = max(new_stock, 10)
    new_stock = min(new_stock, 3000)

    cursor.execute(
        "UPDATE py_product SET stock = %s WHERE id = %s",
        (new_stock, p['id'])
    )

conn.commit()
log(f"已调整 {len(prods)} 个商品的库存")

# ============================================================
# 4. 在稀疏分类中补充新商品
# ============================================================
log("\n=== 4. 补充新商品 ===")

# Check which suppliers exist
cursor.execute("SELECT DISTINCT supplierId FROM py_product WHERE supplierId IS NOT NULL")
supplier_ids = [s['supplierId'] for s in cursor.fetchall()]

new_products = [
    # 烘焙速食 - 糕点 (categoryId=60)
    {"cat": 60, "products": [
        ("手工蛋挞皮30只", 15.9, 18.8, 120),
        ("葡式蛋挞液500g", 12.8, 16.9, 80),
        ("提拉米苏蛋糕420g", 28.8, 35.0, 60),
        ("肉松小贝250g", 16.8, 22.0, 90),
        ("雪媚娘糯米糍240g", 14.8, 19.9, 75),
    ]},
    # 烘焙速食 - 方便速食 (categoryId=61)
    {"cat": 61, "products": [
        ("酸辣粉速食装260gx3", 16.9, 22.9, 200),
        ("螺蛳粉正宗300gx3", 24.9, 32.0, 180),
        ("自热小火锅400g", 29.9, 39.8, 120),
        ("葱油拌面酱料包200g", 9.9, 14.8, 150),
    ]},
    # 烘焙速食 - 饼干零食 (categoryId=62)
    {"cat": 62, "products": [
        ("日式小圆饼100gx3", 12.8, 16.9, 180),
        ("手撕面包棒400g", 15.8, 22.0, 140),
        ("海苔肉松卷150g", 9.9, 15.8, 120),
    ]},
    # 营养保健 - 冲调饮品 (categoryId=63)
    {"cat": 63, "products": [
        ("纯豆浆粉500g", 18.8, 25.0, 100),
        ("黑芝麻核桃粉600g", 28.8, 38.0, 80),
        ("每日坚果燕麦片400g", 22.8, 32.0, 120),
    ]},
    # 营养保健 - 健康食品 (categoryId=64)
    {"cat": 64, "products": [
        ("全麦面包450g", 9.9, 14.8, 80),
        ("奇亚籽250g", 19.8, 28.0, 60),
        ("即食鸡胸肉100gx7", 39.8, 49.0, 100),
    ]},
    # 营养保健 - 预制菜 (categoryId=65)
    {"cat": 65, "products": [
        ("宫保鸡丁料理包300g", 16.8, 24.0, 120),
        ("鱼香肉丝料理包280g", 15.8, 22.0, 120),
        ("红烧肉料理包350g", 22.8, 32.0, 100),
    ]},
    # 优选专享 - 进口零食 (categoryId=67)
    {"cat": 67, "products": [
        ("韩国海苔碎40gx4", 19.8, 28.0, 80),
        ("日本抹茶饼干120g", 25.8, 38.0, 60),
        ("泰国芒果干200g", 22.8, 32.0, 90),
        ("瑞士莲巧克力100g", 29.8, 42.0, 70),
    ]},
    # 茶饮蛋品 - 茶叶 (categoryId=49)
    {"cat": 49, "products": [
        ("茉莉花茶100g", 25.8, 38.0, 60),
        ("铁观音浓香型250g", 48.0, 68.0, 50),
    ]},
    # 水产海鲜 - 鱼类 (categoryId=53)
    {"cat": 53, "products": [
        ("冰鲜三文鱼柳200g", 38.0, 52.0, 40),
        ("巴沙鱼柳500g", 16.8, 24.0, 80),
    ]},
    # 粮油调味 - 干调干货 (categoryId=59)
    {"cat": 59, "products": [
        ("花椒粒50g", 8.9, 12.8, 60),
        ("干辣椒段100g", 9.8, 15.0, 80),
        ("八角桂皮组合装30g", 6.8, 10.0, 60),
    ]},
]

total_new = 0
for group in new_products:
    cat_id = group["cat"]
    for name, price, orig_price, stock in group["products"]:
        supplier_id = random.choice(supplier_ids)
        # Check if product already exists
        cursor.execute("SELECT id FROM py_product WHERE name = %s LIMIT 1", (name,))
        if cursor.fetchone():
            continue
        cursor.execute(
            """INSERT INTO py_product
               (name, categoryId, supplierId, price, originalPrice, stock, sales,
                status, isHot, isNew, mainImage, createTime, updateTime)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 1, %s, %s, %s, NOW(), NOW())""",
            (name, cat_id, supplier_id, price, orig_price, stock,
             random.randint(10, 60),
             1 if random.random() < 0.2 else 0,  # 20% hot items
             1 if random.random() < 0.3 else 0,  # 30% new items
             "/upload/default_product.jpg")
        )
        total_new += 1

conn.commit()
log(f"新增 {total_new} 个商品")

# ============================================================
# 5. 为部分商品标记热销/新品状态，使其更真实
# ============================================================
log("\n=== 5. 调整商品状态标记 ===")

cursor.execute("""
    SELECT id, sales FROM py_product WHERE status = 1 ORDER BY sales DESC LIMIT 10
""")
top_sellers = cursor.fetchall()
for p in top_sellers:
    cursor.execute("UPDATE py_product SET isHot = 1 WHERE id = %s", (p['id'],))

cursor.execute("""
    SELECT id, createTime FROM py_product
    WHERE status = 1 ORDER BY id DESC LIMIT 15
""")
new_products = cursor.fetchall()
for p in new_products:
    cursor.execute("UPDATE py_product SET isNew = 1 WHERE id = %s", (p['id'],))

conn.commit()
log("已更新热销/新品标记")

# ============================================================
# 6. 为订单补充更丰富的时间分布（增加4月-5月数据）
# ============================================================
log("\n=== 6. 创建一批新的4-5月订单 ===")

cursor.execute("""
    SELECT id, supplierId FROM py_product WHERE status = 1
""")
products = cursor.fetchall()
products_map = {}
for p in products:
    if p['supplierId'] not in products_map:
        products_map[p['supplierId']] = []
    products_map[p['supplierId']].append(p['id'])

cursor.execute("SELECT id FROM py_user WHERE role = 'user'")
users = [u['id'] for u in cursor.fetchall()]

if users and products_map:
    # Generate orders from mid-April to early May 2026
    start_date = datetime(2026, 4, 15)
    end_date = datetime(2026, 5, 1)

    order_statuses = ['completed', 'completed', 'completed', 'completed', 'shipped', 'pending']
    pay_methods = ['wechat', 'alipay', 'wechat', 'alipay', 'wechat']

    # Chinese provinces/cities for realistic addresses
    addresses = [
        ("北京市", "北京市", "朝阳区", "朝阳路XX号小区3号楼"),
        ("上海市", "上海市", "浦东新区", "张江路XX弄XX号"),
        ("广东省", "广州市", "天河区", "体育西路XX号"),
        ("广东省", "深圳市", "南山区", "科技园南路XX号"),
        ("浙江省", "杭州市", "西湖区", "文三路XX号"),
        ("江苏省", "南京市", "鼓楼区", "中山北路XX号"),
        ("四川省", "成都市", "武侯区", "科华北路XX号"),
        ("湖北省", "武汉市", "洪山区", "珞瑜路XX号"),
        ("福建省", "厦门市", "思明区", "厦禾路XX号"),
        ("湖南省", "长沙市", "芙蓉区", "五一大道XX号"),
    ]

    names = ["张先生", "李女士", "王先生", "刘女士", "陈先生", "赵女士", "周先生", "吴女士"]
    phones = ["13800138001", "13900139002", "13700137003", "13600136004", "13500135005"]

    new_order_count = 0
    new_item_count = 0

    for day_offset in range((end_date - start_date).days + 1):
        date = start_date + timedelta(days=day_offset)

        # 3-8 orders per day
        orders_today = random.randint(3, 8)
        for _ in range(orders_today):
            user_id = random.choice(users)
            # Assign to a random supplier
            supplier_id = random.choice(list(products_map.keys()))
            supplier_products = products_map[supplier_id]

            if len(supplier_products) < 2:
                continue

            hour = random.randint(7, 21)
            minute = random.randint(0, 59)
            create_time = date.replace(hour=hour, minute=minute, second=random.randint(0, 59))

            # Pick 2-6 items
            num_items = random.randint(2, 6)
            selected_prods = random.sample(supplier_products, min(num_items, len(supplier_products)))

            # Get product details
            items_data = []
            total = 0
            for pid in selected_prods:
                cursor.execute("SELECT id, name, price FROM py_product WHERE id = %s", (pid,))
                p = cursor.fetchone()
                if not p:
                    continue
                qty = random.choices([1, 2, 3], weights=[5, 3, 1])[0]
                item_total = round(p['price'] * qty, 2)
                total += item_total
                items_data.append((p, qty, item_total))

            if not items_data:
                continue

            address = random.choice(addresses)
            name = random.choice(names)
            phone = random.choice(phones)
            status = random.choice(order_statuses)
            pay_method = random.choice(pay_methods)

            cursor.execute(
                """INSERT INTO py_order
                   (orderNo, userId, supplierId, totalAmount, payAmount, discountAmount,
                    status, payStatus, payMethod, payTime,
                    receiverName, receiverPhone, receiverProvince, receiverCity,
                    receiverDistrict, receiverAddress,
                    shippingStatus, createTime, updateTime)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                           %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (f"ORD{create_time.strftime('%Y%m%d')}{random.randint(1000,9999)}",
                 user_id, supplier_id, round(total, 2), round(total, 2), 0,
                 status, 'paid' if status != 'pending' else 'pending',
                 pay_method, create_time if status != 'pending' else None,
                 name, phone, address[0], address[1], address[2], address[3],
                 'pending' if status == 'pending' else 'shipped',
                 create_time, create_time)
            )
            order_id = cursor.lastrowid

            for p, qty, item_total in items_data:
                cursor.execute(
                    """INSERT INTO py_order_item
                       (orderId, productId, productName, price, quantity, totalAmount)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (order_id, p['id'], p['name'], p['price'], qty, item_total)
                )
                new_item_count += 1

            new_order_count += 1

    conn.commit()
    log(f"新增 {new_order_count} 个订单，{new_item_count} 个商品项")

# ============================================================
# 7. 最终更新商品销量
# ============================================================
log("\n=== 7. 最终更新商品销量 ===")

cursor.execute("""
    SELECT oi.productId, SUM(oi.quantity) as total_qty
    FROM py_order_item oi
    JOIN py_order o ON oi.orderId = o.id
    WHERE o.status IN ('completed', 'shipped', 'paid')
    GROUP BY oi.productId
""")
final_sales = cursor.fetchall()

for s in final_sales:
    cursor.execute(
        "UPDATE py_product SET sales = %s WHERE id = %s",
        (s['total_qty'], s['productId'])
    )

conn.commit()
log(f"最终更新 {len(final_sales)} 个商品的销量")

# ============================================================
# 8. 更新浏览历史记录
# ============================================================
log("\n=== 8. 更新浏览历史 ===")

cursor.execute("SELECT id, categoryId FROM py_product WHERE status = 1")
all_prods = cursor.fetchall()

cursor.execute("SELECT id FROM py_product WHERE status = 1 ORDER BY sales DESC LIMIT 30")
hot_product_ids = [p['id'] for p in cursor.fetchall()]

browse_date_start = datetime.now() - timedelta(days=30)
active_users = users[:30]  # 30 active users

for user_id in active_users:
    for _ in range(random.randint(5, 20)):
        weight = random.random()
        if weight < 0.6:
            p = next((x for x in all_prods if x['id'] in hot_product_ids[:10]), random.choice(all_prods))
        else:
            p = random.choice(all_prods)

        days_ago = random.randint(0, 29)
        hour = random.randint(8, 22)
        browse_time = browse_date_start + timedelta(days=days_ago, hours=hour)

        try:
            cursor.execute(
                """INSERT INTO py_user_browse_history
                   (user_id, item_id, behavior_type, item_category, time, createtime, updatetime)
                   VALUES (%s, %s, %s, %s, %s, NOW(), NOW())""",
                (str(user_id), str(p['id']),
                 random.choice([1, 2, 3]),  # 1=view, 2=favorite, 3=cart
                 str(p['categoryId']),
                 browse_time.strftime('%Y-%m-%d %H'))
            )
        except Exception:
            pass

conn.commit()
log("已补充浏览历史记录")

cursor.close()
conn.close()
log("\n=== 数据调整完成! ===")
