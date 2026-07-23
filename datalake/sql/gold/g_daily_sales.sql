-- g_daily_sales.sql — Gold daily sales (join silver finance + dim_store)
INSERT INTO gold.daily_sales (d, store_id, store_name, revenue, cogs, gross_profit, orders, units, aov, upt)
SELECT
    f.d,
    f.store_id,
    s.name AS store_name,
    f.revenue,
    f.cogs,
    f.gross_profit,
    f.orders,
    f.units,
    f.aov,
    f.upt
FROM silver.daily_sales_finance f
JOIN silver.dim_store s ON s.store_id = f.store_id
ON CONFLICT (d, store_id) DO UPDATE SET
    store_name = EXCLUDED.store_name,
    revenue = EXCLUDED.revenue,
    cogs = EXCLUDED.cogs,
    gross_profit = EXCLUDED.gross_profit,
    orders = EXCLUDED.orders,
    units = EXCLUDED.units,
    aov = EXCLUDED.aov,
    upt = EXCLUDED.upt;
