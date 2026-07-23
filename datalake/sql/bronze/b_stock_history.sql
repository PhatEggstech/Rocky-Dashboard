-- b_stock_history.sql — Extract stock history from POS to bronze
INSERT INTO bronze.stock_history (id, warehouse_id, product_id, quantity, end_stock, cost_price, create_at, _batch_id, _extracted_at)
SELECT
    "Id"::text,
    "WarehouseId"::text,
    "ProductId"::text,
    "Quantity"::float,
    "EndStock"::float,
    "CostPrice"::float,
    "CreateAt",
    :batch_id,
    NOW()
FROM "StockHistory"
WHERE "CreateAt" > :watermark
ON CONFLICT (id) DO UPDATE SET
    quantity = EXCLUDED.quantity,
    end_stock = EXCLUDED.end_stock,
    cost_price = EXCLUDED.cost_price,
    _batch_id = EXCLUDED._batch_id,
    _extracted_at = EXCLUDED._extracted_at;
