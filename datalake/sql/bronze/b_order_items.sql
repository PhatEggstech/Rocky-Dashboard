-- b_order_items.sql — Extract order items from POS to bronze
INSERT INTO bronze.order_items (id, order_id, product_id, quantity, unit_price, total_cost_price, delete_at, _batch_id, _extracted_at)
SELECT
    "Id"::text,
    "OrderId"::text,
    "ProductId"::text,
    "Quantity"::float,
    "UnitPrice"::float,
    "TotalCostPrice"::float,
    "DeleteAt",
    :batch_id,
    NOW()
FROM "OrderItem"
WHERE "UpdateAt" > :watermark
ON CONFLICT (id) DO UPDATE SET
    quantity = EXCLUDED.quantity,
    unit_price = EXCLUDED.unit_price,
    total_cost_price = EXCLUDED.total_cost_price,
    delete_at = EXCLUDED.delete_at,
    _batch_id = EXCLUDED._batch_id,
    _extracted_at = EXCLUDED._extracted_at;
