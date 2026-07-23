-- s_00_dim_store.sql — Store dimension from bronze.sites
INSERT INTO silver.dim_store (store_id, name, code, region, province, staff_count)
SELECT
    s.id AS store_id,
    s.name,
    s.code,
    CASE
        WHEN s.province_code IN ('01','02','04','06','08','10','11','12','14','15','17','19','20','22','24','25','26') THEN 'Bắc'
        WHEN s.province_code IN ('38','40','42','44','45','46','48','49','51','52','54','56') THEN 'Trung'
        ELSE 'Nam'
    END AS region,
    s.province_code AS province,
    0 AS staff_count
FROM bronze.sites s
WHERE s.delete_at IS NULL
ON CONFLICT (store_id) DO UPDATE SET
    name = EXCLUDED.name,
    code = EXCLUDED.code,
    region = EXCLUDED.region,
    province = EXCLUDED.province;
