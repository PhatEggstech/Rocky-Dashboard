-- b_sites.sql — Extract sites from POS to bronze
INSERT INTO bronze.sites (id, name, code, province_code, district_code, address, delete_at, _batch_id, _extracted_at)
SELECT
    "Id"::text,
    "Name"::text,
    "Code"::text,
    "ProvinceCode"::text,
    "DistrictCode"::text,
    "Address"::text,
    "DeleteAt",
    :batch_id,
    NOW()
FROM "Site"
WHERE "UpdateAt" > :watermark
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    code = EXCLUDED.code,
    province_code = EXCLUDED.province_code,
    address = EXCLUDED.address,
    delete_at = EXCLUDED.delete_at,
    _batch_id = EXCLUDED._batch_id,
    _extracted_at = EXCLUDED._extracted_at;
