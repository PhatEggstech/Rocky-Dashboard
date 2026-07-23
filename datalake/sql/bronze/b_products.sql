-- b_products.sql — Extract products from POS to bronze
INSERT INTO bronze.products (id, name, code, category_id, brand_id, sell_price, cost_price, delete_at, _batch_id, _extracted_at)
SELECT
    "Id"::text,
    "Name"::text,
    "Code"::text,
    "CategoryId"::text,
    "BrandId"::text,
    "SellPrice"::float,
    "CostPrice"::float,
    "DeleteAt",
    :batch_id,
    NOW()
FROM "Product"
WHERE "UpdateAt" > :watermark
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    code = EXCLUDED.code,
    category_id = EXCLUDED.category_id,
    sell_price = EXCLUDED.sell_price,
    cost_price = EXCLUDED.cost_price,
    delete_at = EXCLUDED.delete_at,
    _batch_id = EXCLUDED._batch_id,
    _extracted_at = EXCLUDED._extracted_at;
