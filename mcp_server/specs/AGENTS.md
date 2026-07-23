# AGENTS.md — Rocky Lens Dashboard

> **Mục đích:** File này là điểm khởi đầu cho mọi AI agent khi mở dự án. Đọc file này TRƯỚC KHI làm bất cứ gì.

---

## 1. Project Overview

**Rocky Lens Dashboard** là hệ thống BI/analytics cho chuỗi cửa hàng kính mắt HMK (Rocky), gồm:
- **Executive Dashboard** (B2C retail): KPI tài chính, khách hàng, tồn kho, chất lượng — dùng data pipeline từ POS PostgreSQL
- **B2B Dashboard**: Quản lý doanh thu/công nợ/chuyển đổi app cho kênh đại lý
- **Conversation Analytics**: AI phân tích hội thoại Zalo giữa Sales Admin và đại lý

## 2. Architecture (30-second version)

```
POS PostgreSQL (255 tables) → Lakehouse (Bronze/Silver/Gold) → FastAPI → React 19 SPA
                              ↘ pos_sync.py → SQLite (legacy fallback) ↗
```

- **Frontend:** React 19 + Vite 6 + TypeScript 5.8 + Tailwind CSS 4 + Recharts
- **Backend:** FastAPI + psycopg_pool (gold.*) + SQLite fallback
- **Pipeline:** Airflow → extract.py → Bronze (PG) → Silver SQL → Gold → API
- **Deploy:** Docker Compose + Nginx + VPS

## 3. File Map (Where to Find What)

| Need | File/Directory |
|------|----------------|
| **Full spec (tổng hợp)** | `ROCKY_LENS_COMPLETE_SPEC.md` |
| **KPI formulas** | `DASHBOARD_FORMULAS.md` |
| **Data flow diagrams** | `DATA_FLOW.md` |
| **Tech stack table** | `TECHSTACK.md` |
| **POS schema (ER + data dictionary)** | `schema-pos-postgresql-da.md` |
| **POS all columns (255 tables)** | `schema-pos-postgresql-columns.md` (6500 lines) |
| **Data field validation** | `DATA_FIELDS_VALIDATION.md` |
| **New metrics SQL** | `planning_new_metrics_architecture.md` |
| **UI design brief** | `design-brief-executive.md` |
| **Backend functions** | `executive-dashboard-functions.md` |
| **QA issues + fixes** | `edp-qa-context-and-fix-checklist.md` |
| **Deploy guide** | `deploy-vps-company.md`, `deploy-vps-quickstart.md` |
| **Project analysis (full)** | `PROJECT_ANALYSIS.md` |
| **KPI descriptions (Notion)** | `notion-dashboard-extracts/kpi-descriptions/` |
| **Conversation Analytics src** | `rk-conversation-analytics-main/` |
| **B2B Dashboard src** | `rk-dashboard-main/` |
| **Agent skills** | `.cortex/skills/rocky-lens-dashboard/` |
| **Context files** | `.cortex/context/` |
| **Harness log** | `harness-handoff.md` |

## 4. Coding Conventions

### Python (Backend)
- FastAPI + Uvicorn
- SQLite via stdlib `sqlite3`; PostgreSQL via `psycopg` 3.x
- Functions in `react_logic.py` return dict payloads; routers just wire them
- ENV-driven config: `POS_PG_DSN`, `EDP_USE_WAREHOUSE`, etc.
- Soft delete: always filter `DeleteAt IS NULL` on POS tables
- Timezone: convert UTC → `Asia/Ho_Chi_Minh` before date truncation

### TypeScript (Frontend)
- React 19 + Vite 6 + Tailwind CSS 4
- State-based routing (no react-router): `useState<PageType>`
- Charts: always wrap in `<ResponsiveContainer width="100%" height={...}>`
- API calls: `src/lib/api.ts` wrapper with typed responses
- Class merging: `cn()` from `src/lib/utils.ts` (clsx + tailwind-merge)
- Icons: Lucide React only

### SQL (Lakehouse)
- Silver naming: `s_00_dim_*.sql` (dims first), `s_daily_*.sql`, `s_monthly_*.sql`, `s_*_z_*.sql` (depends on prior mart)
- Gold naming: `g_00_*.sql` (passthrough), `g_*.sql`
- Convention: `INSERT ... ON CONFLICT DO UPDATE` for idempotency
- Bronze: snake_case columns, `d DATE` derived from timestamp, `_batch_id`

## 5. Smoke Tests (Run Before Committing)

```bash
# Python compile check
python -m py_compile executive_dashboard/app/main.py
python -m py_compile executive_dashboard/app/react_logic.py

# Full smoke (no external DB needed)
pip install -r requirements.txt
pip install -r executive_dashboard/requirements.txt
python tools/smoke_test_all.py

# Frontend build check
cd executive_dashboard_frontend && npm run build

# TypeScript check
cd executive_dashboard_frontend && npx tsc --noEmit
```

## 6. Key Decisions & Do's / Don'ts

### DO:
- Read `ROCKY_LENS_COMPLETE_SPEC.md` for full context
- Check `.cortex/context/` for domain-specific patterns before coding
- Use `NULLIF(x, 0)` in SQL division to prevent divide-by-zero
- Cap extreme values (stock_cover_days max 3650, percentages 0-100)
- Follow existing payload structure in `react_logic.py`
- Update `harness-handoff.md` after significant changes

### DON'T:
- Don't hardcode POS credentials (use ENV)
- Don't query POS primary directly (use read replica / lakehouse)
- Don't add react-router (state-based routing is intentional)
- Don't use mock data in production paths (check `seed.py` guards)
- Don't modify `schema-pos-postgresql-columns.md` manually (auto-generated)
- Don't commit `.env.pg` or `data/edp.sqlite3`

## 7. Adding New Features (Quick Reference)

| Task | Reference |
|------|-----------|
| Add new KPI | `.cortex/skills/rocky-lens-dashboard/templates/new-kpi-checklist.md` |
| Add new page | `.cortex/skills/rocky-lens-dashboard/templates/new-page-checklist.md` |
| Understand KPI formulas | `.cortex/context/kpi-formulas.md` |
| Work with pipeline | `.cortex/context/data-pipeline.md` |
| Frontend patterns | `.cortex/context/frontend-patterns.md` |
| API reference | `.cortex/context/api-endpoints.md` |

## 8. RBAC Roles

| Role | Scope | Pages |
|------|-------|-------|
| `ceo` | All stores | All 9 pages |
| `bod` | All stores | All 9 pages |
| `cfo` | All stores | Executive, Quality, Leaderboard, CSAT, Rev/Staff |
| `om` | All stores | Executive, Sales, Inventory, Quality, Leaderboard |
| `rsm` | By region_id | Executive, Sales, Leaderboard, CSAT, Rev/Staff |
| `sup` | By region_id | Executive, Sales, Leaderboard |
| `store_manager` | By store_id | Executive, Sales, Quality (own store) |

## 9. Data Sources

| Source | Connection | Usage |
|--------|-----------|-------|
| POS PostgreSQL | `POS_PG_DSN` (private network) | 21 tables extracted |
| ZNS PostgreSQL | `ZNS_PG_DSN` (optional) | CSAT ratings |
| Warehouse PG | `WAREHOUSE_PG_DSN` (localhost:5433) | Gold layer serving |
| SQLite | `executive_dashboard/data/edp.sqlite3` | Legacy/fallback mart |
| MinIO | localhost:9000 | Parquet archive |

---

_Last updated: 2026-05-25. Update this file when architecture changes._
