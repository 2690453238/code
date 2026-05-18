"""
Generate historical order data (Jan 1 - Apr 30, 2026) with strong predictable patterns.
Each product has one of three patterns:
- daily_anchor: sells every day (stable volume)
- weekly_regular: sells on specific weekdays only
- occasional: rarely sells (mostly 0)
"""
import random
import time as tm
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict

from utils.db_utils import execute_query, get_db_connection

random.seed(42)

COMMUNITY_SUPPLIER = {'COMM001': 5, 'COMM002': 6, 'COMM003': 7, 'COMM004': 8, 'COMM005': 9}

USERS_BY_COMMUNITY = {
    'COMM001': [2, 13, 18, 23, 28, 33, 38, 43, 48, 53, 58],
    'COMM002': [4, 14, 19, 24, 29, 34, 39, 44, 49, 54, 59],
    'COMM003': [10, 15, 20, 25, 30, 35, 40, 45, 50, 55],
    'COMM004': [11, 16, 21, 26, 31, 36, 41, 46, 51, 56],
    'COMM005': [12, 17, 22, 27, 32, 37, 42, 47, 52, 57],
}

PRODUCTS_BY_SUPPLIER = {
    5: [81, 84, 85, 87, 89, 90, 91, 97, 98, 135, 136, 137, 138, 139, 150,
        338, 340, 343, 345, 353, 356, 363, 366, 368, 369, 375, 378, 380,
        388, 390, 392, 395, 410, 411, 415, 417, 423, 427, 435, 443, 451],
    6: [82, 83, 86, 88, 92, 93, 94, 95, 96, 140, 141, 142, 143, 144,
        339, 341, 344, 350, 352, 362, 371, 372, 374, 376, 377, 384, 394,
        396, 400, 407, 413, 414, 424, 434, 438, 445, 447, 448],
    7: [99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110,
        145, 146, 147, 148, 149, 349, 367, 382, 387, 389, 391, 397, 398,
        399, 404, 408, 422, 428, 431, 433, 437, 439, 444, 461],
    8: [111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121,
        351, 354, 357, 359, 364, 365, 379, 381, 385, 393, 409, 416, 419,
        421, 429, 441, 442, 452, 453, 454, 457, 459, 460],
    9: [122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134,
        342, 346, 347, 348, 355, 358, 360, 361, 370, 373, 383, 386, 401,
        402, 403, 405, 406, 412, 418, 420, 425, 426, 430, 432, 436, 440,
        446, 449, 450, 455, 456, 458],
}

SURNAMES = ['张', '王', '李', '刘', '陈', '杨', '黄', '赵', '周', '吴']
GIVEN_NAMES = ['伟', '强', '磊', '军', '勇', '杰', '涛', '明', '超', '秀英', '秀兰', '丽', '敏', '静']
DISTRICTS = {
    'COMM001': ('湖北省', '武汉市', '洪山区'),
    'COMM002': ('湖北省', '武汉市', '江岸区'),
    'COMM003': ('湖北省', '武汉市', '武昌区'),
    'COMM004': ('湖北省', '武汉市', '汉阳区'),
    'COMM005': ('湖北省', '武汉市', '江夏区'),
}
STREETS = ['中山大道', '解放大道', '建设大道', '和平大道', '珞喻路', '关山大道']
COMMUNITY_NAMES = ['小区', '花园', '社区', '家园']

HOUR_DIST = list(range(7, 23))
HOUR_WEIGHTS = [0.073, 0.064, 0.047, 0.060, 0.061, 0.067, 0.069, 0.056,
                0.059, 0.057, 0.058, 0.068, 0.057, 0.064, 0.066, 0.064]

# === Pattern definitions per product ===
# Each product assigned to: daily_anchor, weekly_regular, or occasional
PRODUCT_PATTERN = {}       # pid -> 'daily_anchor' | 'weekly_regular' | 'occasional'
PATTERN_CONFIG = {
    'daily_anchor': {'pct': 1.00, 'base_qty_range': (9, 11), 'noise': 0.1},
    'weekly_regular': {'pct': 0.00, 'base_qty_range': (3, 7), 'noise': 0.1},
    'occasional': {'pct': 0.00, 'sale_prob': 0.00, 'qty_range': (1, 3)},
}

# Weekly regulars: which days they sell
WEEKLY_ACTIVE_DAYS = {}   # pid -> set of weekdays (0=Mon, 6=Sun)

product_prices = {}
product_names = {}
product_images = {}


def assign_patterns():
    """Assign each product a pattern and configure it"""
    for sid, pids in PRODUCTS_BY_SUPPLIER.items():
        random.shuffle(pids)
        n = len(pids)
        n_anchor = int(n * PATTERN_CONFIG['daily_anchor']['pct'])
        n_regular = int(n * PATTERN_CONFIG['weekly_regular']['pct'])

        for i, pid in enumerate(pids):
            if i < n_anchor:
                PRODUCT_PATTERN[pid] = 'daily_anchor'
            elif i < n_anchor + n_regular:
                PRODUCT_PATTERN[pid] = 'weekly_regular'
                # Assign 2-4 active days per week
                active_days = random.sample(range(7), random.randint(2, 4))
                WEEKLY_ACTIVE_DAYS[pid] = set(active_days)
            else:
                PRODUCT_PATTERN[pid] = 'occasional'


def get_qty_for_product(pid, date_obj):
    """Determine quantity for a product on a given date based on its pattern"""
    pattern = PRODUCT_PATTERN[pid]
    cfg = PATTERN_CONFIG[pattern]
    dow = date_obj.weekday()
    is_weekend = dow >= 5

    if pattern == 'daily_anchor':
        base = random.uniform(*cfg['base_qty_range'])
        # Day-of-week adjustments (consistent pattern)
        dow_factor = {0: 1.00, 1: 1.00, 2: 1.00, 3: 1.00, 4: 1.00, 5: 1.00, 6: 1.00}
        base *= dow_factor.get(dow, 1.0)
        noise = random.uniform(-cfg['noise'], cfg['noise'])
        return max(1, int(round(base + noise)))

    elif pattern == 'weekly_regular':
        if dow in WEEKLY_ACTIVE_DAYS.get(pid, set()):
            base = random.uniform(*cfg['base_qty_range'])
            if is_weekend:
                base *= 1.15
            noise = random.uniform(-cfg['noise'], cfg['noise'])
            return max(1, int(round(base + noise)))
        else:
            return 0

    else:  # occasional
        if random.random() < cfg['sale_prob']:
            return random.randint(*cfg['qty_range'])
        return 0


def generate_data():
    """Main generation function"""
    # Load product info
    products = execute_query('SELECT id, name, price, mainImage, categoryId FROM py_product WHERE status = 1')
    for p in products:
        pid = p['id']
        product_prices[pid] = float(p['price'])
        product_names[pid] = p['name']
        product_images[pid] = p.get('mainImage', '') or ''

    assign_patterns()

    # Print pattern distribution
    for pattern in ['daily_anchor', 'weekly_regular', 'occasional']:
        count = sum(1 for v in PRODUCT_PATTERN.values() if v == pattern)
        print(f'  {pattern}: {count} products')

    result = execute_query('SELECT MAX(id) as mx FROM py_order')
    next_order_id = (result[0]['mx'] or 0) + 1
    result = execute_query('SELECT MAX(id) as mx FROM py_order_item')
    next_item_id = (result[0]['mx'] or 0) + 1

    start_date = datetime(2026, 1, 1)
    end_date = datetime(2026, 5, 18)
    total_days = (end_date - start_date).days + 1
    print(f"\nGenerating {start_date.date()} to {end_date.date()} ({total_days} days)")

    order_sql = """INSERT INTO py_order (id, supplierId, orderNo, userId, totalAmount, payAmount,
        discountAmount, couponId, couponAmount, status, payStatus, payMethod, payTime,
        shippingStatus, shippingTime, trackingNumber, shippingCompany, logisticsInfo,
        deliveryTime, remark, receiverName, receiverPhone, receiverProvince, receiverCity,
        receiverDistrict, receiverAddress, receiverPostcode, createTime, updateTime)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""

    item_sql = """INSERT INTO py_order_item (id, orderId, productId, skuId, productName, skuName,
        productImage, reviewContent, reviewRating, reviewTime, price, quantity, totalAmount, createTime)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""

    total_orders = 0
    total_items = 0
    current_date = start_date

    # Daily order target
    day_weights = {0: 0.85, 1: 0.90, 2: 0.95, 3: 1.00, 4: 1.05, 5: 1.20, 6: 1.15}
    daily_base = 600

    while current_date <= end_date:
        weight = day_weights.get(current_date.weekday(), 1.0)
        orders_today = max(200, int(daily_base * weight + random.uniform(-30, 30)))

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                for comm_code, user_ids in USERS_BY_COMMUNITY.items():
                    supplier_id = COMMUNITY_SUPPLIER[comm_code]
                    n_for_comm = max(1, int(orders_today * len(user_ids) / 52))
                    all_prods = PRODUCTS_BY_SUPPLIER[supplier_id]

                    # Pre-compute quantities for this day (daily anchor amounts)
                    prod_daily_qty = {}
                    for pid in all_prods:
                        q = get_qty_for_product(pid, current_date)
                        if q > 0:
                            prod_daily_qty[pid] = q

                    if not prod_daily_qty:
                        continue

                    # Build probability weights proportional to daily qty
                    prod_ids = list(prod_daily_qty.keys())
                    prod_weights = [prod_daily_qty[p] for p in prod_ids]

                    for _ in range(n_for_comm):
                        user_id = random.choice(user_ids)
                        hour = random.choices(HOUR_DIST, weights=HOUR_WEIGHTS, k=1)[0]
                        order_dt = current_date.replace(
                            hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59)
                        )
                        create_time = order_dt.strftime('%Y-%m-%d %H:%M:%S')

                        num_items = random.choices([3, 4, 5, 6, 7, 8],
                                                   weights=[0.10, 0.20, 0.30, 0.20, 0.15, 0.05], k=1)[0]

                        total_amount = Decimal('0.00')
                        used_pids = set()

                        for _ in range(num_items):
                            # Pick product weighted by daily quantity (avoid repeats in same order)
                            candidates = [(i, p) for i, p in enumerate(prod_ids) if p not in used_pids]
                            if not candidates:
                                break
                            idx = random.choices(range(len(candidates)),
                                                 weights=[prod_weights[candidates[i][0]] for i in range(len(candidates))],
                                                 k=1)[0]
                            pid = candidates[idx][1]
                            used_pids.add(pid)

                            price = Decimal(str(product_prices[pid]))
                            # Use the product's daily quantity as the item quantity
                            item_qty = random.choices([2, 3], weights=[0.70, 0.30], k=1)[0]
                            item_total = price * item_qty
                            total_amount += item_total

                            cursor.execute(item_sql, (
                                next_item_id, next_order_id, pid, None, product_names.get(pid, ''), None,
                                product_images.get(pid, ''), None, None, None,
                                price, item_qty, item_total, create_time
                            ))
                            next_item_id += 1
                            total_items += 1

                        if total_amount == 0:
                            continue

                        # Receiver info
                        name = random.choice(SURNAMES) + random.choice(GIVEN_NAMES)
                        phone = f"1{random.choice(['3','5','7','8','9'])}0{random.randint(10000000, 99999999)}"
                        prov, city, dist = DISTRICTS[comm_code]
                        address = f"{random.choice(STREETS)}{random.choice(COMMUNITY_NAMES)}{random.randint(1,30)}栋{random.randint(1,3)}单元{random.randint(101,3001)}室"

                        days_from_end = (end_date - current_date).days
                        if days_from_end > 3:
                            status = random.choices(['completed', 'paid', 'shipped', 'pending'],
                                                    weights=[0.88, 0.07, 0.04, 0.01], k=1)[0]
                        else:
                            status = random.choices(['completed', 'paid', 'shipped', 'pending'],
                                                    weights=[0.50, 0.25, 0.15, 0.10], k=1)[0]

                        pay_method = None
                        pay_status = 'unpaid'
                        pay_time = None
                        shipping_status = 'unshipped'
                        shipping_time = None

                        if status != 'pending':
                            pay_method = random.choices(['wechat', 'alipay', 'bank'],
                                                        weights=[0.50, 0.30, 0.20], k=1)[0]
                            pay_status = 'paid'
                            pt = order_dt + timedelta(minutes=random.randint(1, 60))
                            pay_time = pt.strftime('%Y-%m-%d %H:%M:%S')

                        if status in ('shipped', 'completed'):
                            shipping_status = 'shipped'
                            st = order_dt + timedelta(days=1, hours=random.randint(8, 16))
                            shipping_time = st.strftime('%Y-%m-%d %H:%M:%S')

                        if status == 'completed':
                            st = order_dt + timedelta(days=random.randint(1, 2), hours=random.randint(8, 16))
                            shipping_time = st.strftime('%Y-%m-%d %H:%M:%S')

                        order_no = f"ORD{order_dt.strftime('%Y%m%d%H%M%S')}{random.randint(1000,9999)}{next_order_id % 100:02d}"

                        cursor.execute(order_sql, (
                            next_order_id, supplier_id, order_no, user_id, total_amount, total_amount,
                            Decimal('0.00'), None, Decimal('0.00'),
                            status, pay_status, pay_method, pay_time,
                            shipping_status, shipping_time, None, None, None, None, '',
                            name, phone, prov, city, dist, address, '430000',
                            create_time, create_time
                        ))
                        next_order_id += 1
                        total_orders += 1

            conn.commit()
            dow = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][current_date.weekday()]
            print(f"  {current_date.date()} ({dow}): {orders_today} orders, {total_items} items")
        except Exception as e:
            conn.rollback()
            print(f"ERROR {current_date.date()}: {e}")
            raise
        finally:
            conn.close()

        current_date += timedelta(days=1)

    print(f"\nDone! {total_orders} orders, {total_items} items")
    return total_orders, total_items


if __name__ == '__main__':
    t0 = tm.time()
    print(f"Start: {datetime.now()}")
    generate_data()
    print(f"Time: {tm.time() - t0:.1f}s")
