-- b_orders.sql — Extract orders from POS to bronze
INSERT INTO bronze.orders (id, customer_id, site_id, need_pay_amount, total_cost_price, complete_at, delete_at, _batch_id, _extracted_at)
SELECT
    "Id"::text,
    "CustomerId"::text,
    "SiteId"::text,
    "NeedPayAmount"::float,
    "TotalCostPrice"::float,
    "CompleteAt" AT TIME ZONE 'Asia/Ho_Chi_Minh',
    "DeleteAt",
    :batch_id,
    NOW()
FROM "Order"
WHERE "CompleteAt" > :watermark
ON CONFLICT (id) DO UPDATE SET
    need_pay_amount = EXCLUDED.need_pay_amount,
    total_cost_price = EXCLUDED.total_cost_price,
    complete_at = EXCLUDED.complete_at,
    delete_at = EXCLUDED.delete_at,
    _batch_id = EXCLUDED._batch_id,
    _extracted_at = EXCLUDED._extracted_at;
