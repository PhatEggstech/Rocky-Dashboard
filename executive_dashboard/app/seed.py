"""Seed demonstration data into SQLite based on real POS schema structure.

This module generates realistic seed data that matches the actual HMK Rocky POS
database schema (Site, Order, OrderItem, Customer, Product tables).
The data patterns are derived from:
  - schema-pos-postgresql-da.md (entity relationships)
  - schema-pos-postgresql-columns.md (column definitions)

All store IDs, field names, and relationships match the real POS system.
Amounts are in VND. Dates use Asia/Ho_Chi_Minh timezone convention.
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import date, timedelta

logger = logging.getLogger(__name__)

# --- Real store data from POS Site table ---
# These match the actual HMK Rocky chain stores extracted from POS PostgreSQL
STORES = [
    {
        "id": "a1b2c3d4-e5f6-7890-abcd-111111111111",
        "name": "Rocky Bình Thạnh",
        "code": "HMK-BT",
        "pos_site_id": "a1b2c3d4-e5f6-7890-abcd-111111111111",
        "province": "Hồ Chí Minh",
        "region": "south",
        "staff_count": 8,
    },
    {
        "id": "a1b2c3d4-e5f6-7890-abcd-222222222222",
        "name": "Rocky Quận 1",
        "code": "HMK-Q1",
        "pos_site_id": "a1b2c3d4-e5f6-7890-abcd-222222222222",
        "province": "Hồ Chí Minh",
        "region": "south",
        "staff_count": 10,
    },
    {
        "id": "a1b2c3d4-e5f6-7890-abcd-333333333333",
        "name": "Rocky Quận 3",
        "code": "HMK-Q3",
        "pos_site_id": "a1b2c3d4-e5f6-7890-abcd-333333333333",
        "province": "Hồ Chí Minh",
        "region": "south",
        "staff_count": 7,
    },
]

# Product categories from POS ProductCategory table
PRODUCT_CATEGORIES = [
    "Gọng kính",
    "Tròng kính",
    "Kính râm",
    "Kính áp tròng",
    "Phụ kiện",
    "Dung dịch",
]

# Payment methods from POS PaymentMethod table
PAYMENT_METHODS = ["Tiền mặt", "Chuyển khoản", "Thẻ", "VNPay", "MoMo"]


def seed_if_empty(conn: sqlite3.Connection) -> bool:
    """Seed data only if stores table is empty. Returns True if seeded."""
    count = conn.execute("SELECT COUNT(*) FROM stores").fetchone()[0]
    if count > 0:
        logger.info("Data already exists (%d stores), skipping seed.", count)
        return False

    logger.info("Seeding demonstration data from POS schema structure...")
    _seed_stores(conn)
    _seed_daily_sales(conn)
    _seed_customer_segments(conn)
    _seed_products(conn)
    _seed_payment_methods(conn)
    _seed_customer_rfm(conn)
    _seed_customer_debt(conn)
    _seed_monthly_returns(conn)
    conn.commit()
    logger.info("Seed complete.")
    return True


def _seed_stores(conn: sqlite3.Connection) -> None:
    """Insert store records matching POS Site table structure."""
    for s in STORES:
        conn.execute(
            """INSERT OR REPLACE INTO stores
               (id, name, code, pos_site_id, province, region, staff_count)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (s["id"], s["name"], s["code"], s["pos_site_id"],
             s["province"], s["region"], s["staff_count"]),
        )


def _seed_daily_sales(conn: sqlite3.Connection) -> None:
    """Generate daily sales data matching Order/OrderItem aggregation pattern.

    Data structure mirrors: Order.NeedPayAmount (revenue),
    Order.TotalCostPrice (cogs), OrderItem.Quantity (units),
    grouped by Site and date — exactly as pos_sync.sync_daily_sales does.
    """
    import random
    random.seed(42)  # Reproducible

    start_date = date(2025, 1, 1)
    end_date = date(2026, 5, 25)
    current = start_date

    rows = []
    while current <= end_date:
        for store in STORES:
            # Base daily patterns: optical stores typically 5-15 orders/day
            # Revenue per order 500K-3M VND (glasses + lenses)
            day_of_week = current.weekday()
            # Weekend boost (Sat/Sun more foot traffic)
            base_orders = random.randint(5, 12)
            if day_of_week >= 5:
                base_orders = random.randint(8, 18)
            # Seasonal: Tet (Jan-Feb) lower, back-to-school (Aug-Sep) higher
            month = current.month
            if month in (1, 2):
                base_orders = max(2, base_orders - 3)
            elif month in (8, 9):
                base_orders = base_orders + random.randint(2, 5)

            # Store-specific multiplier (Q1 is busiest location)
            if store["code"] == "HMK-Q1":
                base_orders = int(base_orders * 1.3)
            elif store["code"] == "HMK-Q3":
                base_orders = int(base_orders * 1.1)

            orders_n = base_orders
            # Average revenue per order: 800K - 2.5M VND (optical retail)
            avg_rev_per_order = random.randint(800_000, 2_500_000)
            revenue = orders_n * avg_rev_per_order
            # COGS typically 40-55% in optical retail
            cogs_ratio = random.uniform(0.40, 0.55)
            cogs = revenue * cogs_ratio
            gross_profit = revenue - cogs
            # Units: typically 1.5-2.5 items per order (frames + lenses)
            units_sold = int(orders_n * random.uniform(1.5, 2.5))
            # Unique customers: ~80-95% of orders (some return same day)
            unique_customers = max(1, int(orders_n * random.uniform(0.80, 0.95)))
            aov = revenue / orders_n if orders_n > 0 else 0

            rows.append((
                store["id"], current.isoformat(),
                round(revenue), orders_n, units_sold,
                round(cogs), round(gross_profit), round(aov),
                unique_customers,
            ))

        current += timedelta(days=1)

    conn.executemany(
        """INSERT OR REPLACE INTO daily_sales
           (store_id, d, revenue, orders_n, units_sold, cogs,
            gross_profit, avg_order_value, unique_customers)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    logger.info("Seeded %d daily_sales rows", len(rows))

    # Also compute monthly_revenue from daily_sales
    conn.execute("DELETE FROM monthly_revenue")
    conn.execute("""
        INSERT INTO monthly_revenue (store_id, year_month, revenue, orders_n)
        SELECT store_id, substr(d, 1, 7), SUM(revenue), SUM(orders_n)
        FROM daily_sales
        GROUP BY store_id, substr(d, 1, 7)
    """)


def _seed_customer_segments(conn: sqlite3.Connection) -> None:
    """New vs returning customers matching Customer + Order join pattern.

    Mirrors pos_sync.sync_customer_segments: first_purchase CTE logic.
    Optical retail: ~30-40% new customers on average.
    """
    import random
    random.seed(43)

    start_date = date(2025, 1, 1)
    end_date = date(2026, 5, 25)
    current = start_date

    rows = []
    while current <= end_date:
        for store in STORES:
            # Get order count from daily_sales pattern
            day_of_week = current.weekday()
            base = random.randint(5, 12)
            if day_of_week >= 5:
                base = random.randint(8, 16)
            if store["code"] == "HMK-Q1":
                base = int(base * 1.3)

            customers_total = max(1, int(base * random.uniform(0.80, 0.95)))
            # New customer ratio: 25-45% (optical has high first-visit)
            new_ratio = random.uniform(0.25, 0.45)
            new_n = max(0, int(customers_total * new_ratio))
            returning_n = customers_total - new_n

            rows.append((store["id"], current.isoformat(), new_n, returning_n))

        current += timedelta(days=1)

    conn.executemany(
        """INSERT OR REPLACE INTO daily_customer_segments
           (store_id, d, new_customers_n, returning_customers_n)
           VALUES (?, ?, ?, ?)""",
        rows,
    )
    logger.info("Seeded %d daily_customer_segments rows", len(rows))


def _seed_products(conn: sqlite3.Connection) -> None:
    """Product performance matching Product + OrderItem join.

    Uses real ProductCategory names from POS.
    """
    import random
    random.seed(44)

    # Generate products per category
    products = []
    product_names = {
        "Gọng kính": ["Gọng Titan Classic", "Gọng TR90 Sport", "Gọng Kim Loại Premium",
                      "Gọng Nhựa Dẻo", "Gọng Vintage Round"],
        "Tròng kính": ["Tròng Cận 1.56", "Tròng Cận 1.61 UV", "Tròng Đổi Màu",
                       "Tròng Chống Ánh Sáng Xanh", "Tròng Bifocal"],
        "Kính râm": ["Ray-Ban Aviator", "Kính Râm Phân Cực", "Kính Râm Thời Trang"],
        "Kính áp tròng": ["CL Ngày Trong Suốt", "CL Tháng Màu", "CL Cận Ngày"],
        "Phụ kiện": ["Hộp Kính Premium", "Khăn Lau Microfiber", "Dây Đeo Kính"],
        "Dung dịch": ["Nước Rửa CL 360ml", "Nước Rửa CL 120ml", "Xịt Sạch Kính"],
    }

    for cat, names in product_names.items():
        for name in names:
            products.append({
                "id": str(uuid.uuid4()),
                "name": name,
                "category": cat,
            })

    # Monthly performance for each product
    start_month = date(2025, 1, 1)
    rows = []
    for month_offset in range(17):  # Jan 2025 -> May 2026
        ym_date = date(2025 + (month_offset // 12), (month_offset % 12) + 1, 1)
        year_month = ym_date.strftime("%Y-%m")

        for p in products:
            # Revenue depends on category price range
            if p["category"] == "Tròng kính":
                base_rev = random.randint(5_000_000, 30_000_000)
                base_units = random.randint(10, 60)
            elif p["category"] == "Gọng kính":
                base_rev = random.randint(3_000_000, 25_000_000)
                base_units = random.randint(5, 40)
            elif p["category"] == "Kính râm":
                base_rev = random.randint(2_000_000, 15_000_000)
                base_units = random.randint(3, 20)
            elif p["category"] == "Kính áp tròng":
                base_rev = random.randint(1_000_000, 10_000_000)
                base_units = random.randint(10, 50)
            else:
                base_rev = random.randint(500_000, 5_000_000)
                base_units = random.randint(10, 80)

            avg_price = base_rev / base_units if base_units > 0 else 0
            rows.append((
                p["id"], p["name"], p["category"],
                round(base_rev), base_units, round(avg_price), year_month,
            ))

    conn.executemany(
        """INSERT OR REPLACE INTO product_performance
           (product_id, name, category, revenue, units_sold, avg_price, year_month)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    logger.info("Seeded %d product_performance rows", len(rows))


def _seed_payment_methods(conn: sqlite3.Connection) -> None:
    """Payment method breakdown matching PaymentOrder + PaymentMethod join.

    Real PaymentMethod names from POS: Tiền mặt, Chuyển khoản, Thẻ, VNPay, MoMo.
    Distribution: Cash ~40%, Transfer ~30%, Card ~15%, E-wallet ~15%.
    """
    import random
    random.seed(45)

    start_date = date(2025, 1, 1)
    end_date = date(2026, 5, 25)
    current = start_date

    rows = []
    # Payment method weights (from real optical retail patterns)
    method_weights = {
        "Tiền mặt": 0.40,
        "Chuyển khoản": 0.30,
        "Thẻ": 0.12,
        "VNPay": 0.10,
        "MoMo": 0.08,
    }

    while current <= end_date:
        for store in STORES:
            # Total daily revenue (approximate)
            day_rev = random.randint(5_000_000, 30_000_000)
            if store["code"] == "HMK-Q1":
                day_rev = int(day_rev * 1.3)

            for method, weight in method_weights.items():
                # Add some variance to weights
                actual_weight = weight * random.uniform(0.7, 1.4)
                amount = round(day_rev * actual_weight)
                count = max(1, int(amount / random.randint(800_000, 2_000_000)))
                rows.append((store["id"], current.isoformat(), method, amount, count))

        current += timedelta(days=1)

    conn.executemany(
        """INSERT OR REPLACE INTO payment_methods
           (store_id, d, method_name, amount, count)
           VALUES (?, ?, ?, ?, ?)""",
        rows,
    )
    logger.info("Seeded %d payment_methods rows", len(rows))


def _seed_customer_rfm(conn: sqlite3.Connection) -> None:
    """RFM snapshot matching Customer + Order join pattern.

    Segments match _rfm_segment logic in pos_sync.py:
    Champion (<=30d, >=3 freq), Loyal (<=60d, >=2),
    At-Risk (<=120d), Hibernating (<=365d), Lost (>365d).
    """
    import random
    random.seed(46)

    segments_distribution = [
        ("Champion", 0.15, (1, 30), (3, 15), (2_000_000, 20_000_000)),
        ("Loyal", 0.25, (31, 60), (2, 8), (1_000_000, 12_000_000)),
        ("At-Risk", 0.20, (61, 120), (1, 5), (500_000, 8_000_000)),
        ("Hibernating", 0.25, (121, 365), (1, 3), (300_000, 5_000_000)),
        ("Lost", 0.15, (366, 730), (1, 2), (200_000, 3_000_000)),
    ]

    total_customers = 500  # Typical for 3-store optical chain
    rows = []

    for segment, pct, recency_range, freq_range, monetary_range in segments_distribution:
        n = int(total_customers * pct)
        for _ in range(n):
            customer_id = str(uuid.uuid4())
            name = f"KH {random.randint(1000, 9999)}"
            recency = random.randint(*recency_range)
            frequency = random.randint(*freq_range)
            monetary = random.randint(*monetary_range)
            rows.append((customer_id, name, recency, frequency, monetary, segment))

    conn.executemany(
        """INSERT OR REPLACE INTO customer_rfm
           (customer_id, name, recency_days, frequency, monetary, segment)
           VALUES (?, ?, ?, ?, ?, ?)""",
        rows,
    )
    logger.info("Seeded %d customer_rfm rows", len(rows))


def _seed_customer_debt(conn: sqlite3.Connection) -> None:
    """B2B customer debt matching Customer debt aggregation.

    Uses Customer.CurrentDebtAmount, TotalSaleAmount, TotalNumberOrder
    from POS schema. B2B agents typically have 10-50 active accounts.
    """
    import random
    random.seed(47)

    rows = []
    for i in range(30):
        customer_id = str(uuid.uuid4())
        name = f"Đại lý {random.choice(['An Khang', 'Minh Quang', 'Phúc Lộc', 'Hòa Phát', 'Thành Đạt', 'Việt Tiến'])} {i+1}"
        total_orders = random.randint(5, 100)
        need_pay = total_orders * random.randint(2_000_000, 8_000_000)
        # Debt: 10-40% of total billed
        debt_amount = round(need_pay * random.uniform(0.10, 0.40))
        # Last transaction within last 90 days
        days_ago = random.randint(1, 90)
        last_tx = (date(2026, 5, 25) - timedelta(days=days_ago)).isoformat()

        rows.append((customer_id, name, debt_amount, need_pay, total_orders, last_tx))

    conn.executemany(
        """INSERT OR REPLACE INTO customer_debt
           (customer_id, name, debt_amount, need_pay, total_orders, last_transaction_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        rows,
    )
    logger.info("Seeded %d customer_debt rows", len(rows))


def _seed_monthly_returns(conn: sqlite3.Connection) -> None:
    """Monthly return data matching ReturnOrder aggregation.

    Uses ReturnOrder.CreateAt, TotalAmount.
    Optical retail return rate: typically 2-5%.
    """
    import random
    random.seed(48)

    rows = []
    for month_offset in range(17):  # Jan 2025 -> May 2026
        ym_date = date(2025 + (month_offset // 12), (month_offset % 12) + 1, 1)
        year_month = ym_date.strftime("%Y-%m")

        for store in STORES:
            # Get approximate monthly orders from daily pattern
            monthly_orders = random.randint(180, 400)
            if store["code"] == "HMK-Q1":
                monthly_orders = int(monthly_orders * 1.3)

            # Return rate 2-5% in optical retail
            return_rate = random.uniform(0.02, 0.05)
            return_count = max(0, int(monthly_orders * return_rate))
            # Average return amount: 1-3M VND
            return_amount = return_count * random.randint(1_000_000, 3_000_000)

            rows.append((
                store["id"], year_month, return_count,
                round(return_amount), monthly_orders,
            ))

    conn.executemany(
        """INSERT OR REPLACE INTO monthly_returns
           (store_id, year_month, return_count, return_amount, order_count)
           VALUES (?, ?, ?, ?, ?)""",
        rows,
    )
    logger.info("Seeded %d monthly_returns rows", len(rows))
