---
title: HMK BigData System — Data Flow
last_updated: 2026-05-13
owner: data-platform
related:
  - docs/TECHSTACK.md
  - docs/PROJECT_ANALYSIS.md
  - datalake/README.md
  - docs/schema-pos-postgresql-da.md
---

# Data flow — HMK BigData System

Diagram chi tiết luồng dữ liệu end-to-end của hệ thống: từ **POS PostgreSQL** (source
of truth) đến **dashboard React** mà user nhìn thấy. Tài liệu này dùng kèm
`docs/TECHSTACK.md` (liệt kê công nghệ) và `datalake/README.md` (chi tiết
mapping KPI ↔ gold tables).

Toàn bộ diagram dưới đây viết bằng **Mermaid** — render được trên GitHub, Cursor,
VS Code (extension Markdown Preview Mermaid), Obsidian. Bản PNG/SVG đã render sẵn
trong `docs/diagrams/`:

![Data flow overview](diagrams/dataflow_overview.png)

> Re-render khi sửa: `npx -y -p @mermaid-js/mermaid-cli mmdc -i docs/diagrams/dataflow_overview.mmd -o docs/diagrams/dataflow_overview.png -w 2200 -H 1300 --backgroundColor white`

---

## 1. Tổng quan — high-level pipeline

```mermaid
flowchart LR
    subgraph SRC["🟦 SOURCE — POS PostgreSQL"]
        POS[(POS PG\n255 bảng OLTP)]
    end

    subgraph LAKE["🟧 LAKEHOUSE — Datalake pipeline"]
        EXT["extract.py\npython + psycopg"]
        MINIO[(MinIO\nParquet archive)]
        BRONZE[(bronze.*\n21 tables)]
        SILVER[(silver.*\n23 tables)]
        GOLD[(gold.*\n22 tables)]
        EXT --> MINIO
        EXT --> BRONZE
        BRONZE --> SILVER
        SILVER --> GOLD
    end

    subgraph SERVE["🟩 SERVING — FastAPI EDP"]
        WHPOOL["psycopg_pool\nWAREHOUSE pool"]
        SQLITE[(SQLite mart\nlegacy)]
        API["FastAPI\n/api/* /health"]
        WHPOOL --> API
        SQLITE -. fallback .-> API
    end

    subgraph UI["🟪 UI — React + Nginx"]
        NGINX["Nginx\nstatic + /api proxy"]
        REACT["React 19 SPA\nRecharts + Tailwind"]
        NGINX --> REACT
    end

    POS  --> EXT
    GOLD --> WHPOOL
    API  --> NGINX
    POS  -. legacy direct sync .-> SQLITE

    subgraph ORCH["🟨 ORCHESTRATION — Airflow"]
        DAG["hmk_datalake DAG\n0 */2 * * *"]
    end
    DAG --> EXT
    DAG --> SILVER
    DAG --> GOLD
```

**Chú thích:**

- **Đường nét liền** = luồng dữ liệu chính (đang sống).
- **Đường nét đứt** = luồng legacy (đang phase-out khi `EDP_USE_WAREHOUSE=1` ổn định).
- Mỗi mũi tên xanh từ `POS` đi qua `extract.py` mang 21 bảng nguồn (xem `datalake/sql/bronze/*.sql`).

---

## 2. Lakehouse chi tiết — Bronze → Silver → Gold

```mermaid
flowchart TB
    classDef src fill:#dbeafe,stroke:#1d4ed8
    classDef bronze fill:#fed7aa,stroke:#c2410c
    classDef silver fill:#e5e7eb,stroke:#4b5563
    classDef gold fill:#fde68a,stroke:#b45309
    classDef code fill:#fefce8,stroke:#854d0e,stroke-dasharray: 4 2

    POSPG[("POS PostgreSQL\n(public.* — 255 bảng)")]:::src

    subgraph EXTRACT["Bronze extraction — datalake/lib/extract.py"]
        SQL["datalake/sql/bronze/b_*.sql\n(21 file, SELECT có watermark)"]:::code
        RETRY["_read_with_retry\n(SerializationFailure retry + timeout)"]:::code
        UUIDFIX["UUID → str cast\nbefore Parquet write"]:::code
    end

    PARQUET[("MinIO\ns3://hmk-datalake/bronze/<table>/<year_month>/<batch>.parquet")]:::code

    subgraph BRONZE_PG["bronze.* — typed PG mirror"]
        B_SO["sale_order\n+sale_channel_id +ecom_source_id\n+exchange_parent_id\n+promotion_discount_amount\n+cost_amount d _batch_id"]:::bronze
        B_SOI["sale_order_item\n+original_price +actual_price\n+is_promotion_gift"]:::bronze
        B_CUST["customer\n+total_sale_amount\n+last_transaction_at\n+customer_group_id"]:::bronze
        B_PROD["product\n+master_unit_id +stock_quantity\n+sale_price_ignore_tax"]:::bronze
        B_DIM["warehouse, product_category,\nbrand, sale_channel,\necom_source, promotion_campaign"]:::bronze
        B_LINK["measurement_ticket_sale_order_item\n(funnel link)"]:::bronze
        B_OTH["site, stock_item, stock_history,\nmeasurement_ticket, cut_ticket,\nreturn_sale_order, supplier_warranty,\npromotion_campaign_sale_order, pos_session"]:::bronze
    end

    subgraph SILVER_PG["silver.* — cleaned + business logic"]
        S_DIM["dim_store dim_warehouse\ndim_brand dim_category dim_product\ndim_channel dim_campaign"]:::silver
        S_DAILY["daily_sales_finance\ndaily_channel_sales\ndaily_campaign_sales\ndaily_customer_segments\ndaily_measurement_funnel"]:::silver
        S_MONTH["monthly_inventory monthly_inventory_sku\nmonthly_inventory_ageing\nmonthly_abc_sku monthly_z_gmroi_category\nmonthly_quality_returns monthly_return_reasons\nmonthly_cohort_retention"]:::silver
        S_SNAP["customer_rfm_snapshot"]:::silver
    end

    subgraph GOLD_PG["gold.* — serving marts (1:1 SQLite mapping)"]
        G_DIM["stores dim_product dim_category\ndim_brand dim_channel dim_campaign"]:::gold
        G_DAILY["daily_sales_finance\ndaily_channel_sales daily_campaign_sales\ndaily_customer_segments\ndaily_measurement_funnel"]:::gold
        G_MONTH["monthly_inventory_sku\nmonthly_inventory_ageing\nmonthly_abc_sku\nmonthly_gmroi_category\nmonthly_quality_returns\nmonthly_return_reasons\nmonthly_cohort_retention"]:::gold
        G_SNAP["customer_rfm_snapshot"]:::gold
    end

    META[("meta.*\npipeline_runs · quality_checks ·\nlineage · watermarks")]

    POSPG --> SQL --> RETRY --> UUIDFIX
    UUIDFIX --> PARQUET
    UUIDFIX --> B_SO
    UUIDFIX --> B_SOI
    UUIDFIX --> B_CUST
    UUIDFIX --> B_PROD
    UUIDFIX --> B_DIM
    UUIDFIX --> B_LINK
    UUIDFIX --> B_OTH

    B_DIM  --> S_DIM
    B_PROD --> S_DIM
    B_SO   --> S_DAILY
    B_SOI  --> S_DAILY
    B_LINK --> S_DAILY
    B_CUST --> S_DAILY
    B_DIM  --> S_DAILY
    B_OTH  --> S_DAILY
    B_OTH  --> S_MONTH
    B_SOI  --> S_MONTH
    B_SO   --> S_SNAP
    B_CUST --> S_SNAP

    S_DIM   --> G_DIM
    S_DAILY --> G_DAILY
    S_MONTH --> G_MONTH
    S_SNAP  --> G_SNAP

    EXTRACT -.write.-> META
    SILVER_PG -.write.-> META
    GOLD_PG -.write.-> META
```

**Bảng dependency thứ tự bắt buộc trong Silver:**

| Order prefix | File | Dependency |
|---|---|---|
| `s_00_*` | `dim_warehouse, dim_brand, dim_category, dim_product, dim_channel, dim_campaign` | Chỉ phụ thuộc bronze.* |
| `s_daily_*`, `s_monthly_*` (no `z_`) | Daily/monthly marts | Đọc dim_* + bronze |
| `s_monthly_z_gmroi_category` | GMROI | Cần `monthly_inventory_sku` đã sinh trước |
| `s_customer_rfm_snapshot` | RFM | Đọc `daily_sales_finance` |

Naming convention: alphabetical execution → `s_00_*` (dim) ⇒ `s_*` (daily/monthly) ⇒ `s_*_z_*` (depends on prior mart).

---

## 3. Request flow — UI hits dashboard

```mermaid
sequenceDiagram
    autonumber
    actor User as 🧑 User<br/>(CEO / RSM / Store)
    participant Browser as 🌐 Browser
    participant Nginx as edp-web<br/>(Nginx :80)
    participant API as edp-api<br/>(FastAPI :8080)
    participant Pool as psycopg_pool<br/>(WAREHOUSE pool)
    participant PG as postgres-warehouse<br/>(gold.*)
    participant SQLite as SQLite mart<br/>(legacy fallback)

    User->>Browser: Mở http://localhost:3000
    Browser->>Nginx: GET /
    Nginx-->>Browser: index.html + JS bundle
    Browser->>Nginx: GET /api/datalake/status
    Nginx->>API: proxy_pass /api/datalake/status
    API->>Pool: warehouse_status()
    Pool->>PG: SELECT layer, MAX(finished_at) FROM meta.pipeline_runs ...
    PG-->>Pool: rows
    Pool-->>API: status payload
    API-->>Nginx: 200 JSON
    Nginx-->>Browser: 200 JSON

    Browser->>Nginx: GET /api/strategic/board?...
    Nginx->>API: proxy
    alt EDP_USE_WAREHOUSE=1 AND pool ok
        API->>Pool: warehouse_query("SELECT ... FROM gold.daily_sales_finance ...")
        Pool->>PG: SQL
        PG-->>Pool: rows
        Pool-->>API: rows
    else flag off OR pool fail
        API->>SQLite: cursor.execute(...)
        SQLite-->>API: rows
    end
    API-->>Nginx: JSON payload
    Nginx-->>Browser: JSON
    Browser-->>User: render Recharts + KPI cards
```

**Tham chiếu code:**

- Pool/feature flag: `executive_dashboard/app/warehouse.py`
- Legacy SQLite reader: `executive_dashboard/app/react_logic.py`
- Router lakehouse status: `executive_dashboard/app/routers/datalake.py`
- Nginx proxy: `executive_dashboard_frontend/nginx.conf`

---

## 4. Lakehouse pipeline run — Airflow DAG sequence

```mermaid
sequenceDiagram
    autonumber
    participant Cron as Airflow scheduler<br/>(0 */2 * * *)
    participant DAG as DAG hmk_datalake
    participant ExtLib as datalake.lib.extract
    participant POS as POS PG (replica)
    participant Minio as MinIO bucket
    participant WH as Warehouse PG
    participant Meta as meta.pipeline_runs

    Cron->>DAG: trigger
    DAG->>WH: health_check (SELECT 1)
    DAG->>POS: health_check (SELECT 1)
    DAG->>WH: ensure_schemas (idempotent CREATE)
    DAG->>ExtLib: extract_bronze(tables=DEFAULT_TABLES)
    par for each of 21 tables
        ExtLib->>POS: SELECT (with watermark + retry)
        POS-->>ExtLib: DataFrame
        ExtLib->>Minio: PUT parquet
        ExtLib->>WH: COPY/INSERT bronze.<t> + ON CONFLICT
        ExtLib->>Meta: INSERT pipeline_runs (bronze, success)
    end
    DAG->>WH: quality_bronze (row counts + null checks)
    DAG->>WH: transform_silver (run silver/*.sql in order)
    DAG->>Meta: INSERT pipeline_runs (silver, success)
    DAG->>WH: quality_silver
    DAG->>WH: transform_gold (run gold/*.sql)
    DAG->>Meta: INSERT pipeline_runs (gold, success)
    DAG->>WH: quality_gold (gold.stores, gold.daily_sales_finance row>=1)
    DAG-->>Cron: notify_done
```

Manual override:

```bash
# Trigger ngoài Airflow (1 shot full pipeline)
docker compose --profile datalake-run run --rm datalake-run

# Hoặc local Python:
python datalake/scripts/run_pipeline.py full --lookback-days 90
```

---

## 5. Legacy sync path — POS → SQLite (đang phase-out)

```mermaid
flowchart LR
    POS[(POS PG\nreplica)] -- "SELECT mỗi bảng\n(read replica)" --> SYNC["pos_sync.py<br/>chạy trong process FastAPI"]
    SYNC -- "INSERT/UPDATE\nUPSERT theo watermark" --> SQLITE[(SQLite mart\nedp.sqlite3)]
    SQLITE -- "cursor.execute" --> RL["react_logic.py<br/>strategic_logic.py"]
    RL --> APIH["FastAPI handlers"]

    subgraph Trigger
        T1["POS_SYNC_ON_STARTUP=1\n(boot)"]
        T2["POS_SYNC_INTERVAL_SEC=1800\n(periodic)"]
        T3["Manual button\n/api/pos/sync"]
        T4["DAG hmk_pos_to_sqlite_sync\n(Airflow)"]
    end
    T1 -.-> SYNC
    T2 -.-> SYNC
    T3 -.-> SYNC
    T4 -.-> SYNC
```

**Status sync:** quan sát qua `GET /health` → field `pos_sync.last_status` /
`last_message` / `last_sync_at_utc`. Watermark lưu trong bảng `sync_state` (SQLite).

**Migration plan:** khi `tools/validate_warehouse_vs_sqlite.py` ≥ 99% parity, bật
`EDP_USE_WAREHOUSE=1` → `react_logic.py` đọc thẳng `gold.*`, sync legacy được tắt
(`POS_SYNC_INTERVAL_SEC=0`, gỡ DAG cũ).

---

## 6. Docker network — physical view

```mermaid
flowchart TB
    subgraph HOST["💻 Host (Windows/Linux)"]
        direction TB
        subgraph DC["Docker network: bigdatasystem4hmk_default"]
            EDPAPI["edp-api\n:8080 internal\n:8890 host"]
            EDPWEB["edp-web (Nginx)\n:80 internal\n:3000 host"]
            PGWH["postgres-warehouse\n:5432 internal\n:5433 host"]
            MINIO["minio\n:9000/9001"]
            AIR["airflow\n:8080 internal\n:8081 host"]
            INIT["datalake-init / -run\n(one-shot)"]
        end
        POSEXT[("VPN ⇒ POS PG\n10.39.93.19:5432")]
        VOLAPI[(executive_dashboard/data\nSQLite volume)]
        VOLWH[(warehouse_data vol)]
        VOLMIN[(minio_data vol)]
        VOLAIR[(airflow_home vol)]
    end

    EDPWEB  -- "/api/* proxy" --> EDPAPI
    EDPAPI  -- "psycopg_pool" --> PGWH
    EDPAPI  -- "sqlite3 file" --> VOLAPI
    EDPAPI  -- "psycopg over VPN" --> POSEXT
    INIT    -- "DDL + COPY" --> PGWH
    INIT    -- "PUT parquet" --> MINIO
    AIR     -- "DAG tasks" --> PGWH
    AIR     -- "Parquet archive" --> MINIO
    AIR     -- "VPN sync" --> POSEXT
    PGWH    --- VOLWH
    MINIO   --- VOLMIN
    AIR     --- VOLAIR
```

**Cổng đã expose host:**

| Service | Host:Container | URL |
|---------|----------------|-----|
| `edp-web` | 3000:80 | http://localhost:3000 |
| `edp-api` | 8890:8080 | http://localhost:8890 |
| `postgres-warehouse` | 5433:5432 | `psql -h localhost -p 5433 -U hmk` |
| `minio` (API) | 9000:9000 | http://localhost:9000 |
| `minio` (Console) | 9001:9001 | http://localhost:9001 |
| `airflow` | 8081:8080 | http://localhost:8081 |

---

## 7. Data contracts (tóm tắt)

| Contract | Quy ước | Nơi enforce |
|----------|---------|-------------|
| Timezone cắt ngày | `SYNC_TZ=Asia/Ho_Chi_Minh` → `d DATE` derived | `datalake/lib/loader.py:DATE_SOURCE`, `pos_sync.py` |
| Currency | VND, đơn vị **đồng** nguyên (số nguyên), không cent | Bronze giữ `DOUBLE PRECISION`; serving cast int |
| New vs returning customer | First purchase < lookback window (mặc định 90d) | `silver/s_daily_customer_segments.sql` |
| Funnel link | `bronze.measurement_ticket_sale_order_item` → SaleOrderItem → SaleOrder | `silver/s_daily_measurement_funnel.sql` |
| Inventory unit | 1 row `bronze.stock_item` = 1 unit; sold from `sale_order_item.quantity` | `silver/s_monthly_inventory*.sql` |
| Soft delete | Mọi bảng có `delete_at` ≠ NULL bị loại trong silver | Silver WHERE clauses |
| GMROI dependency | Cần `monthly_inventory_sku` chạy xong | filename `s_monthly_z_gmroi_category.sql` |

Đầy đủ data contract POS: `docs/schema-pos-postgresql-da.md` §12.

---

## 8. Quick reference — KPI ↔ Gold table ↔ UI page

| Page React | KPI/chart | Gold table | Silver script |
|-----------|-----------|-----------|---------------|
| Executive Summary | Revenue, GPM, channel mix | `daily_sales_finance`, `daily_channel_sales`, `monthly_z_gmroi_category` | `s_daily_sales_finance.sql`, `s_daily_channel_sales.sql`, `s_monthly_z_gmroi_category.sql` |
| Sales & Marketing | Campaign perf, customer mix, funnel | `daily_campaign_sales`, `daily_customer_segments`, `daily_measurement_funnel` | `s_daily_campaign_sales.sql`, `s_daily_customer_segments.sql`, `s_daily_measurement_funnel.sql` |
| Inventory & Supply Chain | ABC, ageing, GMROI treemap | `monthly_abc_sku`, `monthly_inventory_ageing`, `monthly_gmroi_category` | `s_monthly_abc_sku.sql`, `s_monthly_inventory_ageing.sql`, `s_monthly_z_gmroi_category.sql` |
| Quality & CLV | Pareto, RFM, cohort retention | `monthly_return_reasons`, `customer_rfm_snapshot`, `monthly_cohort_retention` | `s_monthly_return_reasons.sql`, `s_customer_rfm_snapshot.sql`, `s_monthly_cohort_retention.sql` |

Bảng đầy đủ + công thức: `datalake/README.md` mục **"KPI & dashboard"**.
