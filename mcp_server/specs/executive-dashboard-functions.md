---
title: Executive Dashboard Functions
created: 2026-05-11
author: AI-assisted
last_updated: 2026-05-11
updated_by: AI-assisted
status: active
---

# Executive Dashboard Functions

Tài liệu này liệt kê các chức năng chính của thư mục `executive_dashboard/`: backend FastAPI, SQLite snapshot, đồng bộ PostgreSQL POS, API cho React dashboard, legacy dashboard, AI Q&A và vận hành Docker.

## 1. Vai trò của `executive_dashboard/`

`executive_dashboard/` là backend chính của hệ thống HMK Vision Dashboard.

Luồng dữ liệu:

```text
PostgreSQL POS / POS replica
        ↓ sync_from_postgres
SQLite snapshot: executive_dashboard/data/edp.sqlite3
        ↓ FastAPI API
React frontend / Legacy HTML dashboard
```

Backend không để frontend query trực tiếp POS. Dữ liệu POS được sync về SQLite trước, sau đó các API dashboard đọc SQLite để phản hồi nhanh và giảm tải database POS.

## 2. Cấu trúc folder chính

| Path | Chức năng |
|------|-----------|
| `app/main.py` | Entry point FastAPI, startup, health/readiness, sync orchestration, ops readiness, AI endpoint, semantic contract. |
| `app/db.py` | Kết nối SQLite, khởi tạo schema, migration nhẹ, index phục vụ query dashboard. |
| `app/pos_sync.py` | Đồng bộ PostgreSQL POS sang SQLite, incremental sync, sync state, sync runs, default SQL theo schema POS. |
| `app/react_logic.py` | Business logic cho React dashboard: executive summary, sales, inventory, quality/CLV, drill-down detail. |
| `app/routers/react_dashboard.py` | Router `/api/react/*` cho frontend React. |
| `app/routers/strategic.py` | Router chiến lược/brief/chart detail: `/api/strategic/*`, `/api/brief/*`. |
| `app/routers/legacy_dashboard.py` | Router legacy dashboard: stores, dashboard, heatmap, targets, preview month. |
| `app/strategic_logic.py` | Logic KPI strategic board theo 4 trụ Finance, Customer, Inventory, Goal. |
| `app/brief_logic.py` | Logic executive brief summary và store growth. |
| `app/chart_detail.py` | Logic giải thích nguồn dữ liệu và breakdown cho từng chart. |
| `app/logic.py` | Hàm nền tảng: date parsing, target calculation, aggregate period, heatmap bands. |
| `app/deps.py` | Helper RBAC/scope theo role `ceo`, `rsm`, `store_manager`. |
| `app/kpi_contract.py` | Semantic KPI contract: mapping KPI theo role và nguồn bảng POS. |
| `app/openrouter_ai.py` | Tích hợp OpenRouter cho AI Q&A. |
| `app/seed.py` | Seed dữ liệu demo và đồng bộ strategic demo data khi SQLite mới/rỗng. |
| `app/schemas.py` | Pydantic schemas cho request body. |
| `templates/index.html` | Legacy HTML dashboard page. |
| `static/app.js` | Legacy dashboard JavaScript. |
| `static/style.css` | CSS legacy dashboard. |
| `data/` | SQLite runtime data, ví dụ `edp.sqlite3`. Không commit dữ liệu thật. |
| `.env.pg.example` | Mẫu env kết nối POS, sync, OpenRouter, logging. |
| `Dockerfile` | Build FastAPI backend container, expose container port `8080`. |
| `requirements.txt` | Python dependencies của backend. |
| `run_edp.ps1`, `run_edp.bat` | Script chạy local trên Windows. |

## 3. Startup và runtime

Khi FastAPI startup, `app/main.py` thực hiện:

1. Nạp `executive_dashboard/.env.pg` nếu tồn tại.
2. Validate các env quan trọng: `POS_SYNC_INTERVAL_SEC`, `POS_SYNC_QUERY_TIMEOUT_MS`, `OPENROUTER_TIMEOUT_SEC`, `OPENROUTER_RETRIES`.
3. Mở SQLite qua `get_conn()`.
4. Đảm bảo schema bằng `ensure_strategic_schema()`.
5. Seed dữ liệu demo nếu SQLite rỗng bằng `seed_if_empty()`.
6. Đồng bộ strategic demo data bằng `sync_strategic_demo_data()`.
7. Nếu `POS_SYNC_ON_STARTUP` bật, chạy `sync_from_postgres()`.
8. Nếu `POS_SYNC_INTERVAL_SEC > 0`, tạo background loop sync định kỳ.

Backend có cơ chế recover SQLite khi gặp lỗi `database disk image is malformed`: đổi tên DB hỏng sang file backup `.corrupt-*`, khởi tạo lại schema mới.

## 4. SQLite snapshot và bảng dữ liệu

SQLite nằm tại:

```text
executive_dashboard/data/edp.sqlite3
```

Các nhóm bảng chính:

| Nhóm | Bảng SQLite |
|------|-------------|
| Master data | `regions`, `stores`, `holidays` |
| Target & legacy KPI | `monthly_targets`, `daily_revenue`, `daily_store_signals` |
| Finance | `daily_sales_finance` |
| Channel & campaign | `daily_channel_sales`, `daily_campaign_sales` |
| Funnel/customer | `daily_measurement_funnel`, `daily_customer_segments`, `monthly_funnel_steps` |
| Inventory | `monthly_inventory`, `monthly_inventory_sku`, `monthly_inventory_ageing`, `monthly_brand_category_metrics` |
| Quality | `monthly_quality_returns`, `monthly_return_reasons` |
| Payment/session | `daily_payment_methods`, `daily_pos_sessions` |
| RFM | `customer_rfm_snapshot` |
| Sync state | `sync_state`, `sync_runs` |

`sync_state` lưu watermark/status gần nhất để incremental sync không mất trạng thái sau restart. `sync_runs` lưu lịch sử run để vận hành/debug.

## 5. Đồng bộ POS PostgreSQL sang SQLite

Module chính: `app/pos_sync.py`.

Chức năng:

- Đọc `POS_PG_DSN`, `POS_PG_READ_DSN`, hoặc `POS_PG_DSN_IS_READ_REPLICA`.
- Ưu tiên read replica nếu có.
- Hỗ trợ incremental sync theo `pos.last_success_at_utc - POS_SYNC_OVERLAP_DAYS`.
- Chuẩn hóa timezone bằng `POS_SYNC_TIMEZONE`, mặc định `Asia/Ho_Chi_Minh`.
- Hỗ trợ SQL mặc định theo schema POS hoặc SQL override qua env `POS_*_SQL`.
- Ghi kết quả sync vào `sync_state` và `sync_runs`.

Các sync group trong `app/main.py`:

| Group | Sections |
|-------|----------|
| `all` | Tất cả sections |
| `core` | `stores`, `revenue`, `sales_finance`, `targets`, `holidays` |
| `channel` | `channel_sales`, `campaign_sales`, `measurement_funnel`, `customer_segments` |
| `inventory` | `inventory`, `inventory_sku`, `ageing` |
| `inventory_monthly` | `inventory` |
| `inventory_sku` | `inventory_sku` |
| `ageing` | `ageing` |
| `quality` | `quality_returns`, `return_reasons` |
| `payments` | `payments`, `sessions` |
| `customer_rfm` | `customer_rfm` |
| `funnel_steps` | `funnel_steps` |

Sync thủ công:

```bash
curl -X POST "http://127.0.0.1:8890/api/pos/sync/core?wait=true&wait_timeout_sec=600"
curl -X POST "http://127.0.0.1:8890/api/pos/sync/channel?wait=true&wait_timeout_sec=600"
curl -X POST "http://127.0.0.1:8890/api/pos/sync/customer_rfm?wait=true&wait_timeout_sec=600"
```

Theo dõi sync:

```bash
curl "http://127.0.0.1:8890/api/pos/sync/status"
```

## 6. Health, readiness và vận hành

Các endpoint vận hành:

| Endpoint | Chức năng |
|----------|-----------|
| `GET /health` | Kiểm tra app sống, capability, trạng thái POS sync. |
| `GET /ready` | Readiness probe: app startup xong và SQLite mở được. |
| `GET /api/ops/readiness` | Preflight go-live: sync stale, thiếu replica, bảng chính rỗng, coverage dữ liệu. |
| `POST /api/pos/sync` | Trigger sync thủ công, hỗ trợ `group`, `wait`, `wait_timeout_sec`. |
| `POST /api/pos/sync/{group}` | Trigger sync theo group. |
| `GET /api/pos/sync/status` | Trạng thái sync runtime gần nhất. |

`/api/ops/readiness` trả:

- `ok`: có critical issue hay không.
- `status`: `ready` hoặc `blocked`.
- `alerts`: danh sách cảnh báo vận hành.
- `pos_sync`: trạng thái sync.
- `coverage`: số dòng và min/max date của bảng chính.

## 7. API cho React dashboard

Router: `app/routers/react_dashboard.py`, prefix `/api/react`.

| Endpoint | Chức năng |
|----------|-----------|
| `GET /api/react/executive-summary` | Scorecards, revenue, NPM, channel mix, movers, heatmap executive. |
| `GET /api/react/sales-marketing` | Funnel, campaign scatter, customer mix, channel/customer metrics. |
| `GET /api/react/inventory-supply-chain` | KPI tồn kho, GMROI, ABC category, ageing, brand/category metrics. |
| `GET /api/react/quality-clv` | Return/warranty, RFM segments, cohort retention, CLV proxy. |
| `GET /api/react/details/store/{store_id_path}` | Drill-down cửa hàng. |
| `GET /api/react/details/campaign/{campaign_id_path}` | Drill-down campaign. |
| `GET /api/react/details/{detail_id}` | Detail động cho revenue, GPM, funnel, inventory, quality, RFM, live operations. |

Các API React đều nhận:

```text
start=YYYY-MM-DD
end=YYYY-MM-DD
role=ceo|rsm|store_manager
region_id=<optional>
store_id=<optional>
```

Role filtering dùng `filtered_store_ids()`:

- `ceo`: toàn chuỗi, có thể lọc thêm `region_id`.
- `rsm`: bắt buộc `region_id`.
- `store_manager`: bắt buộc `store_id`.

## 8. Strategic và legacy APIs

Router strategic:

| Endpoint | Chức năng |
|----------|-----------|
| `GET /api/strategic/board` | Board 4 trụ Finance, Customer, Inventory, Goal. |
| `GET /api/suggestions/period` | Gợi ý kỳ dữ liệu dựa trên max date trong SQLite. |
| `GET /api/strategic/chart-detail` | Giải thích nguồn và breakdown cho chart. |
| `GET /api/brief/summary` | Executive brief summary. |
| `GET /api/brief/store-growth` | Bảng tăng trưởng cửa hàng. |

Router legacy:

| Endpoint | Chức năng |
|----------|-----------|
| `GET /api/stores` | Danh sách store theo role/scope. |
| `GET /api/dashboard` | Dashboard legacy theo target/actual. |
| `GET /api/heatmap` | Heatmap ngày cho một store. |
| `GET /api/targets` | Lấy target tháng của store. |
| `POST /api/targets` | Cập nhật target tháng. |
| `GET /api/preview-month` | Preview target tháng nếu áp cùng GT. |

Legacy HTML page:

```text
GET /
```

Render `templates/index.html`, dùng `static/app.js` và `static/style.css`.

## 9. Business logic chính

| Module | Chức năng |
|--------|-----------|
| `react_logic.py` | Payload cho React: executive, sales, inventory, quality/CLV, RFM/cohort, detail/drill-down. |
| `strategic_logic.py` | KPI board theo 4 trụ: Finance, Customer, Inventory, Goal. |
| `brief_logic.py` | Executive brief, growth rows. |
| `chart_detail.py` | Chart provenance, công thức, breakdown store. |
| `logic.py` | Date/target/day-kind/aggregate helpers. |

Một số payload quan trọng trong `react_logic.py`:

- `executive_summary_payload()`
- `sales_marketing_payload()`
- `inventory_supply_chain_payload()`
- `quality_clv_payload()`
- `rfm_payload()`
- `cohort_payload()`
- `store_drill_payload()`
- `campaign_drill_payload()`
- `detail_payload()`

## 10. AI Q&A

Endpoint:

```text
POST /api/ai/ask
```

Module: `app/openrouter_ai.py`.

Chức năng:

- Gọi OpenRouter chat completion.
- Nhận `question` và `context`.
- Trả `answer` và `model`.
- Không cho frontend giữ API key.

Env liên quan:

```env
OPENROUTER_API_KEY=
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free
OPENROUTER_SITE_URL=http://127.0.0.1:8890
OPENROUTER_APP_NAME=HMK-visualize
OPENROUTER_TIMEOUT_SEC=45
OPENROUTER_RETRIES=2
```

Nếu thiếu `OPENROUTER_API_KEY`, endpoint trả lỗi rõ ràng.

## 11. Semantic KPI contract

Endpoint:

```text
GET /api/semantic/contract
```

Nguồn: `app/kpi_contract.py`.

Chức năng:

- Liệt kê KPI bắt buộc theo role `ceo`, `rsm`, `store_manager`.
- Map KPI sang bảng/cột POS.
- Mô tả semantic visual layer và drill-down kỳ vọng.

## 12. Cấu hình môi trường

File mẫu:

```text
executive_dashboard/.env.pg.example
```

Các env chính:

| Env | Ý nghĩa |
|-----|---------|
| `POS_PG_DSN` | DSN PostgreSQL POS hoặc POS replica. |
| `POS_PG_READ_DSN` | DSN read replica riêng nếu có. |
| `POS_PG_DSN_IS_READ_REPLICA` | `1` nếu `POS_PG_DSN` đã trỏ tới replica. |
| `POS_SYNC_ON_STARTUP` | `1` sync khi startup, `0` tắt. |
| `POS_SYNC_INTERVAL_SEC` | Sync định kỳ trong FastAPI; `0` là tắt. |
| `POS_SYNC_QUERY_TIMEOUT_MS` | Timeout mỗi query sync. |
| `POS_SYNC_TIMEZONE` | Timezone khi cắt ngày dữ liệu POS. |
| `POS_SYNC_OVERLAP_DAYS` | Overlap incremental để bắt late-arriving orders. |
| `POS_SYNC_INITIAL_LOOKBACK_DAYS` | Lookback lần sync đầu. |
| `POS_*_SQL` | Custom SQL override cho từng bảng snapshot. |
| `OPENROUTER_*` | Cấu hình AI Q&A. |
| `EDP_CORS_ORIGINS` | Origins được phép gọi API khi chạy frontend dev. |
| `EDP_ACCESS_LOG` | Bật access log request. |
| `LOG_LEVEL`, `LOG_FORMAT` | Cấu hình logging. |

Không commit file `.env.pg` thật vì chứa credential.

## 13. Docker và port

`Dockerfile` build FastAPI:

- Base image: `python:3.11-slim`
- Workdir: `/app`
- Copy `app/`, `static/`, `templates/`
- Volume: `/app/data`
- Expose container port: `8080`
- CMD: `uvicorn app.main:app --host 0.0.0.0 --port 8080`

Trong `docker-compose.yml`, container port vẫn là `8080`; host port hiện đang map:

```text
8890:8080
```

Vì vậy API local là:

```text
http://127.0.0.1:8890
```

Frontend Docker vẫn gọi backend nội bộ qua service DNS:

```text
http://edp-api:8080
```

## 14. Lệnh vận hành thường dùng

Chạy local bằng Docker:

```bash
docker compose up -d --build edp-api edp-web
```

Kiểm tra health:

```bash
curl http://127.0.0.1:8890/health
curl http://127.0.0.1:8890/ready
curl http://127.0.0.1:8890/api/ops/readiness
```

Chạy smoke:

```bash
python tools/smoke_edp.py
python tools/smoke_test_all.py
```

Xem logs:

```bash
docker compose logs -f edp-api
```

Restart API:

```bash
docker compose restart edp-api
```

## 15. Lưu ý production

- `executive_dashboard/data/` là runtime state, cần backup định kỳ.
- VPS phải có `.env.pg` thật, không lấy từ Git.
- Nếu VPS không truy cập được POS replica/private IP, sync sẽ không có data.
- Nên dùng `POS_PG_DSN_IS_READ_REPLICA=1` hoặc `POS_PG_READ_DSN` khi nguồn là replica.
- Không bật đồng thời FastAPI periodic sync và Airflow nếu không muốn trùng job.
- `inventory_sku` là nhóm nặng, nên bật riêng khi DB chịu tải.
- `/api/ops/readiness` là endpoint preflight quan trọng trước go-live.
