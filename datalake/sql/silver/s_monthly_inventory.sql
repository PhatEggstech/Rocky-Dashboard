-- s_monthly_inventory.sql — Monthly inventory aggregates per store
INSERT INTO silver.monthly_inventory (year_month, store_id, on_hand_units, inventory_value, dead_stock_pct, stock_cover_days)
SELECT
    TO_CHAR(NOW(), 'YYYY-MM') AS year_month,
    w.site_id AS store_id,
    SUM(i.on_hand) AS on_hand_units,
    SUM(i.on_hand * i.cost_price) AS inventory_value,
    -- Dead stock: products with on_hand > 0 but no sales in 90 days
    COALESCE(
        100.0 * COUNT(CASE WHEN i.on_hand > 0 AND last_sale.last_sold IS NULL THEN 1 END)::float
        / NULLIF(COUNT(CASE WHEN i.on_hand > 0 THEN 1 END), 0),
        0
    ) AS dead_stock_pct,
    -- Stock cover days: on_hand / avg daily sales (capped at 3650)
    LEAST(
        COALESCE(
            SUM(i.on_hand) / NULLIF(avg_sales.daily_units, 0),
            3650
        ),
        3650
    ) AS stock_cover_days
FROM bronze.inventory i
JOIN bronze.warehouses w ON w.id = i.warehouse_id
LEFT JOIN LATERAL (
    SELECT MAX(o.complete_at) AS last_sold
    FROM bronze.order_items oi
    JOIN bronze.orders o ON o.id = oi.order_id
    WHERE oi.product_id = i.product_id
      AND o.site_id = w.site_id
      AND o.complete_at > NOW() - INTERVAL '90 days'
      AND o.delete_at IS NULL
    LIMIT 1
) last_sale ON true
LEFT JOIN LATERAL (
    SELECT COALESCE(SUM(oi2.quantity) / NULLIF(EXTRACT(DAY FROM NOW() - MIN(o2.complete_at)), 0), 0) AS daily_units
    FROM bronze.order_items oi2
    JOIN bronze.orders o2 ON o2.id = oi2.order_id
    WHERE o2.site_id = w.site_id
      AND o2.complete_at > NOW() - INTERVAL '90 days'
      AND o2.delete_at IS NULL
) avg_sales ON true
WHERE w.delete_at IS NULL
GROUP BY 1, 2
ON CONFLICT (year_month, store_id) DO UPDATE SET
    on_hand_units = EXCLUDED.on_hand_units,
    inventory_value = EXCLUDED.inventory_value,
    dead_stock_pct = EXCLUDED.dead_stock_pct,
    stock_cover_days = EXCLUDED.stock_cover_days;
