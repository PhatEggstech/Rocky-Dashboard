-- s_daily_sales_finance.sql — Daily sales & finance metrics per store
INSERT INTO silver.daily_sales_finance (d, store_id, revenue, cogs, gross_profit, orders, units, aov, upt)
SELECT
    o.complete_at::date AS d,
    o.site_id AS store_id,
    SUM(o.need_pay_amount) AS revenue,
    SUM(o.total_cost_price) AS cogs,
    SUM(o.need_pay_amount) - SUM(o.total_cost_price) AS gross_profit,
    COUNT(DISTINCT o.id) AS orders,
    COALESCE(SUM(oi.quantity), 0) AS units,
    SUM(o.need_pay_amount) / NULLIF(COUNT(DISTINCT o.id), 0) AS aov,
    COALESCE(SUM(oi.quantity), 0)::float / NULLIF(COUNT(DISTINCT o.id), 0) AS upt
FROM bronze.orders o
LEFT JOIN bronze.order_items oi ON oi.order_id = o.id AND oi.delete_at IS NULL
WHERE o.delete_at IS NULL
  AND o.complete_at IS NOT NULL
  AND o.need_pay_amount > 0
  AND o.need_pay_amount < 100000000000
GROUP BY 1, 2
ON CONFLICT (d, store_id) DO UPDATE SET
    revenue = EXCLUDED.revenue,
    cogs = EXCLUDED.cogs,
    gross_profit = EXCLUDED.gross_profit,
    orders = EXCLUDED.orders,
    units = EXCLUDED.units,
    aov = EXCLUDED.aov,
    upt = EXCLUDED.upt;
