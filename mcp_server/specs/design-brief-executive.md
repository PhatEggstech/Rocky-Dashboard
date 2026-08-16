---
title: Design Brief — Executive Dashboard (một trang)
created: 2026-05-04
author: AI-assisted / product spec
---

# Mục tiêu màn hình

Trang **tổng hợp** chỉ số chiến lược toàn chuỗi theo trụ **tài chính — vận hành (qua POS) — khách hàng — tồn kho — mục tiêu**. CEO/BOD đánh giá toàn cảnh tiến độ và mức độ bền vững tăng trưởng. Dữ liệu MVP: SQLite + mock có kiểm chứng với `daily_revenue` và bảng mở rộng.

## Data contract KPI (chốt theo vai trò)

### CEO (toàn chuỗi)
- Sales: `gmv_net`, `orders`, `aov`
- Finance: `gross_margin_pct`, `net_margin_pct`, `target_achievement_pct`
- Customer: `new_customers`, `repeat_customer_rate_pct`
- Inventory: `inventory_turnover`, `stockout_risk_sku_n`
- Marketing: `campaign_revenue_share_pct`

### RSM (theo vùng)
- Sales: `gmv_net`, `orders`, `aov`, `top_store_growth`
- Finance: `target_achievement_pct`
- Customer: `repeat_customer_rate_pct`
- Inventory: `inventory_turnover`

### Store Manager (1 CH)
- Sales: `gmv_net`, `orders`, `aov`
- Finance: `target_achievement_pct`
- Customer: `conversion_proxy`, `return_rate_pct`
- Inventory: `low_stock_sku_n`

## Mapping layer chuẩn (DB thật, không mock)

Nguồn chính từ `pos_dev`:
- Sales: `public."SaleOrder"`, `public."SaleOrderItem"`, `public."Site"`
- Customer: `public."Customer"`, `public."SaleOrder"`, `public."PosSession"`
- Inventory: `public."StockItem"`, `public."StockHistory"`, `public."Product"`
- Marketing: `public."PromotionCampaignSaleOrder"` (+ campaign dim liên quan)

Quy tắc mapping:
1. Tất cả KPI có **formula chuẩn** và truy vết đến field gốc.
2. Tách lớp semantic (fact/dim) khỏi lớp hiển thị chart.
3. Không dùng mock khi đã có table/field thật đáp ứng định nghĩa KPI.
4. Mỗi KPI phải có định nghĩa grain (`day/site/region`) rõ ràng.

Chi tiết machine-readable đã publish tại endpoint:
- `GET /api/semantic/contract`

## Visual redesign theo semantic layer

Domain-driven board:
- **Sales:** daily GMV line, Orders+AOV combo, store growth ranked bar
- **Customer:** new vs repeat area, repeat-rate line, cohort heatmap
- **Inventory:** turnover by category, low-stock SKU table, aging stock histogram
- **Finance:** gross/net margin line, target-vs-actual bullet, profit bridge waterfall
- **Marketing:** campaign revenue share donut, campaign ROI bar, discount impact line

Drill-down chuẩn:
- Domain → Region/Site → Day/Order/SKU → transaction detail.

# Layout (đang triển khai UI)

| Vùng | Nội dung |
|------|-----------|
| **Header** | Thời gian, khu vực / vùng chiến lược (CEO), RBAC mock (RSM/SM), chế độ xem (tổng quan / so sánh kỳ), tải dữ liệu |
| **Zone A — Finance** | Net Profit Margin, Revenue per Staff — scorecard + line NPM + bar đ/NV theo vùng |
| **Zone B — Customer** | Churn rate, Basket size (UPT) — line churn + bar UPT theo CH |
| **Zone C — Inventory** | Dead stock %, Stock cover days — bar theo vùng |
| **Zone D — Goal** | % Target Achievement (KPI-023) + bar % đạt theo vùng + CTA drill-down |
| **Bảng** | Tăng trưởng doanh thu (sort / lọc / Export CSV); KPI-023 theo CH (**Export CSV**) |
| **Chi tiết** | Heatmap ngày (KPI-023); tab thiết lập chỉ tiêu |

# Tương tác & export

- Hover: tooltip (giá trị, z-score kỳ nơi có, % vs kỳ trước khi bật *So sánh kỳ*).
- Click chart / vùng: modal drill-down (MVP — mở rộng danh sách giao dịch / CH sau).
- Mọi bảng chính: nút **Export CSV** (tăng trưởng theo bộ lọc; KPI-023 theo dashboard hiện tại).

# Responsive

- Mobile: KPI 1 cột; bộ lọc trong nút “Bộ lọc”; một số chart phụ ẩn (`desktop-only-chart`).

# Bảng KPI (chuẩn quản trị + MVP)

| KPI (EN) | KPI (VI) | Công thức chuẩn | MVP (nguồn) |
|----------|----------|-----------------|---------------|
| Net Profit Margin | Biên LN ròng | LN ròng / Doanh thu | `(1 - cogs_ratio - opex_ratio) * DT` từ POS |
| Revenue per Staff | Doanh thu / NV | DT / headcount | `stores.staff_count` + tổng DT kỳ |
| Churn rate | Tỷ lệ mất khách | KH không mua / KH kỳ trước | `daily_store_signals.churn_rate_pct` (mock ổn định) |
| Basket size (UPT) | SP / đơn | Tổng SP / tổng đơn | `units_n / orders_n` |
| Dead stock % | Tồn chết/chậm | (định nghĩa kho) | `monthly_inventory.dead_stock_pct` |
| Stock cover days | Ngày tồn bao phủ | (định nghĩa kho) | `monthly_inventory.stock_cover_days` |
| % Target achievement | Đạt mục tiêu | Thực / Target | `logic.aggregate_period` + KPI-023 |

# Bản triển khai MVP (code)

| Hạng mục | File / API |
|----------|------------|
| Board trụ A–D + `growth_rows` | `executive_dashboard/app/strategic_logic.py` → **`GET /api/strategic/board`** |
| Schema mở rộng | `executive_dashboard/app/db.py` — `daily_store_signals`, `monthly_inventory`, `stores.staff_count`, `stores.strategic_zone` |
| Đồng bộ demo | `executive_dashboard/app/seed.py` — `sync_strategic_demo_data` (gọi từ startup) |
| KPI-023 + heatmap | `GET /api/dashboard`, `GET /api/heatmap` |
| Legacy brief (GPM/CLV/CSAT/NPS) | `GET /api/brief/summary` *(vẫn có, UI không còn dùng)* |
| UI | `templates/index.html`, `static/app.js`, `static/style.css` |
| RBAC + CEO `region_id` | `app/deps.py` — `filtered_store_ids` |

Cập nhật spec: sửa bảng trên khi nghiệp vụ thay đổi; sau đó rà API + seed.
