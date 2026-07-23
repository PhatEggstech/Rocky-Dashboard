-- s_00_dim_product.sql — Product dimension from bronze
INSERT INTO silver.dim_product (product_id, name, code, category, brand, sell_price)
SELECT
    p.id AS product_id,
    p.name,
    p.code,
    pc.name AS category,
    NULL AS brand,
    p.sell_price
FROM bronze.products p
LEFT JOIN bronze.product_categories pc ON pc.id = p.category_id
WHERE p.delete_at IS NULL
ON CONFLICT (product_id) DO UPDATE SET
    name = EXCLUDED.name,
    code = EXCLUDED.code,
    category = EXCLUDED.category,
    sell_price = EXCLUDED.sell_price;
