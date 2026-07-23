-- b_customers.sql — Extract customers from POS to bronze
INSERT INTO bronze.customers (id, name, phone, email, gender, date_of_birth, site_id, create_at, delete_at, _batch_id, _extracted_at)
SELECT
    "Id"::text,
    "Name"::text,
    "Phone"::text,
    "Email"::text,
    "Gender"::text,
    "DateOfBirth",
    "SiteId"::text,
    "CreateAt",
    "DeleteAt",
    :batch_id,
    NOW()
FROM "Customer"
WHERE "UpdateAt" > :watermark
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    phone = EXCLUDED.phone,
    email = EXCLUDED.email,
    site_id = EXCLUDED.site_id,
    delete_at = EXCLUDED.delete_at,
    _batch_id = EXCLUDED._batch_id,
    _extracted_at = EXCLUDED._extracted_at;
