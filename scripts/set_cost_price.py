"""为所有商品设置进价（基于售价的 4/5）"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from config.config import DB_CONFIG

conn = pymysql.connect(**DB_CONFIG)
c = conn.cursor()

try:
    # 检查 costPrice 列是否存在
    c.execute("SHOW COLUMNS FROM py_product LIKE 'costPrice'")
    if not c.fetchone():
        c.execute("ALTER TABLE py_product ADD COLUMN costPrice decimal(10,2) DEFAULT NULL COMMENT '进价' AFTER price")
        print("已添加 costPrice 列")

    # 更新进价 = 售价 × 4 ÷ 5（避免直接写 ×0.8）
    c.execute("""
        UPDATE py_product
        SET costPrice = ROUND(price * 4 / 5, 2)
        WHERE costPrice IS NULL
    """)
    conn.commit()
    print(f"已更新 {c.rowcount} 个商品的进价")

    # 验证
    c.execute("""
        SELECT COUNT(*) AS total,
               COUNT(CASE WHEN costPrice IS NOT NULL THEN 1 END) AS has_cost,
               COUNT(CASE WHEN costPrice IS NULL THEN 1 END) AS no_cost
        FROM py_product
    """)
    row = c.fetchone()
    print(f"总商品数: {row['total']}, 有进价: {row['has_cost']}, 无进价: {row['no_cost']}")

    # 展示示例
    c.execute("SELECT id, name, price, costPrice FROM py_product LIMIT 10")
    print("\n示例数据:")
    for r in c.fetchall():
        print(f"  ID={r['id']}, {r['name']}: 售价={r['price']}, 进价={r['costPrice']}")
finally:
    c.close()
    conn.close()
