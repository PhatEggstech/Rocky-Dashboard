-- g_monthly_revenue.sql — Gold monthly revenue (aggregate from gold.daily_sales)
INSERT INTO gold.monthly_revenue (year_month, store_id, store_name, revenue, cogs, gross_profit, orders)
SELECT
    TO_CHAR(d, 'YYYY-MM') AS year_month,
    store_id,
    store_name,
    SUM(revenue) AS revenue,
    SUM(cogs) AS cogs,
    SUM(gross_profit) AS gross_profit,
    SUM(orders) AS orders
FROM gold.daily_sales
GROUP BY 1, 2, 3
ON CONFLICT (year_month, store_id) DO UPDATE SET
    store_name = EXCLUDED.store_name,
    revenue = EXCLUDED.revenue,
    cogs = EXCLUDED.cogs,
    gross_profit = EXCLUDED.gross_profit,
    orders = EXCLUDED.orders;
