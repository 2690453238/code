"""第二波调整：增加销量差异化和热门商品数据"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from datetime import datetime, timedelta
from config.config import DB_CONFIG

random.seed(123)

conn = pymysql.connect(**DB_CONFIG)
c = conn.cursor()

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

log("开始加强数据差异化...")

# 1. 找到所有商品及其当前销量
c.execute("""
    SELECT p.id, p.name, p.sales, p.stock, p.price, p.categoryId, p.isHot, p.isNew,
           c.name as catName
    FROM py_product p
    JOIN py_category c ON p.categoryId = c.id
    WHERE p.status = 1
    ORDER BY p.sales DESC
""")
products = c.fetchall()

log(f"共有 {len(products)} 个在线商品")

# 2. 给部分热门商品增加历史销量（模拟前几个月的累积）
#   这样推荐系统能看到真正的热销品
for i, p in enumerate(products):
    # Top 20% products get big sales boost (simulating popularity)
    if i < len(products) * 0.2:
        boost = random.randint(80, 200)
    # Middle 60% get moderate boost
    elif i < len(products) * 0.8:
        boost = random.randint(20, 80)
    # Bottom 20% stay low
    else:
        boost = random.randint(0, 15)

    new_sales = p['sales'] + boost
    c.execute("UPDATE py_product SET sales = %s WHERE id = %s", (new_sales, p['id']))

conn.commit()
log("已调整销量差异化")

# 3. 按价格带合理调整库存
c.execute("SELECT * FROM py_product WHERE status = 1")
prods = c.fetchall()

for p in prods:
    daily_sales = max(p['sales'] / 60.0, 0.05)

    if p['price'] >= 50:
        factor = random.uniform(45, 90)   # 粮油等
    elif p['price'] >= 20:
        factor = random.uniform(14, 35)   # 肉禽蛋奶
    elif p['price'] >= 10:
        factor = random.uniform(5, 15)    # 蔬菜水果
    else:
        factor = random.uniform(3, 8)     # 叶菜

    new_stock = max(int(daily_sales * factor), 5)
    new_stock = min(new_stock, 3000)

    c.execute("UPDATE py_product SET stock = %s WHERE id = %s", (new_stock, p['id']))

conn.commit()
log("已重新调整库存")

# 4. 打印最终结果
c.execute("""
    SELECT p.name, p.sales, p.stock, p.price, c.name as cat
    FROM py_product p JOIN py_category c ON p.categoryId = c.id
    WHERE p.status = 1
    ORDER BY p.sales DESC LIMIT 15
""")
log("\n=== 最终热销TOP 15 ===")
for r in c.fetchall():
    log(f'{r["name"]:25s} | 销量={r["sales"]:>4} | 库存={r["stock"]:>4} | 价格={r["price"]:>5} | {r["cat"]}')

c.execute("SELECT COUNT(*) as c FROM py_order")
log(f'\n总订单数: {c.fetchone()["c"]}')

c.execute("SELECT COUNT(*) as c FROM py_order_item")
log(f'总订单项数: {c.fetchone()["c"]}')

c.execute("SELECT COUNT(*) as c FROM py_product WHERE status=1")
log(f'在线商品数: {c.fetchone()["c"]}')

c.close()
conn.close()
log("完成!")
