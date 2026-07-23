-- g_00_stores.sql — Gold stores dimension (passthrough from silver)
INSERT INTO gold.stores (store_id, name, code, region, province, staff_count)
SELECT store_id, name, code, region, province, staff_count
FROM silver.dim_store
ON CONFLICT (store_id) DO UPDATE SET
    name = EXCLUDED.name,
    code = EXCLUDED.code,
    region = EXCLUDED.region,
    province = EXCLUDED.province,
    staff_count = EXCLUDED.staff_count;
