-- s_daily_customer_segments.sql — New vs returning customers per store per day
INSERT INTO silver.daily_customer_segments (d, store_id, new_customers, returning_customers)
SELECT
    o.complete_at::date AS d,
    o.site_id AS store_id,
    COUNT(DISTINCT CASE WHEN c.create_at::date = o.complete_at::date THEN o.customer_id END) AS new_customers,
    COUNT(DISTINCT CASE WHEN c.create_at::date < o.complete_at::date THEN o.customer_id END) AS returning_customers
FROM bronze.orders o
LEFT JOIN bronze.customers c ON c.id = o.customer_id
WHERE o.delete_at IS NULL
  AND o.complete_at IS NOT NULL
  AND o.need_pay_amount > 0
  AND o.customer_id IS NOT NULL
GROUP BY 1, 2
ON CONFLICT (d, store_id) DO UPDATE SET
    new_customers = EXCLUDED.new_customers,
    returning_customers = EXCLUDED.returning_customers;
