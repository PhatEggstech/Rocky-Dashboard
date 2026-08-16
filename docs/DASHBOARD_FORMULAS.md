# Công thức tính & Nguồn dữ liệu — HMK Executive Dashboard

> Tài liệu mô tả chi tiết **công thức tính** từng KPI trên dashboard và **nguồn dữ liệu POS PostgreSQL** tương ứng.

---

## Mục lục

1. [Tổng quan luồng dữ liệu](#1-tổng-quan-luồng-dữ-liệu)
2. [Bảng SQLite trung gian](#2-bảng-sqlite-trung-gian)
3. [Zone Finance — Tài chính](#3-zone-finance--tài-chính)
4. [Zone Customer — Khách hàng](#4-zone-customer--khách-hàng)
5. [Zone Inventory — Tồn kho](#5-zone-inventory--tồn-kho)
6. [Zone Goal — Mục tiêu KPI](#6-zone-goal--mục-tiêu-kpi)
7. [Sales & Marketing](#7-sales--marketing)
8. [Quality & CLV](#8-quality--clv)
9. [Bảng derived (tự tính sau sync)](#9-bảng-derived)
10. [Mapping POS tables → SQL](#10-mapping-pos-tables--sql)

---

## 1. Tổng quan luồng dữ liệu

```
POS PostgreSQL ──(sync_from_postgres)──► SQLite (edp.sqlite3) ──(logic)──► API JSON ──► Dashboard UI
```

- **POS sync** chạy khi startup hoặc khi user bấm "Đồng bộ POS" hoặc theo `POS_SYNC_INTERVAL_SEC`.
- Mỗi bảng POS có **SQL mặc định** (hardcode trong `pos_sync.py`), có thể override bằng **biến môi trường** (`POS_*_SQL`).
- SQL dùng placeholder `{SYNC_CUTOFF_UTC}` và `{SYNC_TZ}` để sync incremental.

---

## 2. Bảng SQLite trung gian

| Bảng SQLite | PK | Nguồn POS | ENV override |
|---|---|---|---|
| `stores` | `id` | `Site`, `Province`, `SiteGroup` | `POS_STORES_SQL` |
| `regions` | `id` | `Province` | (cùng stores) |
| `daily_revenue` | `store_id, d` | `SaleOrder` | `POS_REVENUE_SQL` |
| `daily_sales_finance` | `store_id, d` | `SaleOrder` + `SaleOrderItem` + `MeasurementTicket` | `POS_SALES_FINANCE_SQL` |
| `daily_store_signals` | `store_id, d` | `SaleOrder` + `SaleOrderItem` | `POS_CUSTOMER_SIGNALS_SQL` |
| `monthly_inventory` | `store_id, year_month` | `StockHistory` + `Warehouse` | `POS_INVENTORY_SQL` |
| `daily_channel_sales` | `store_id, d, channel_name` | `SaleOrder` + `SaleChannel` + `EcomSource` | `POS_CHANNEL_SALES_SQL` |
| `daily_campaign_sales` | `store_id, d, campaign_id` | `PromotionCampaignSaleOrder` + `PromotionCampaign` | `POS_CAMPAIGN_SALES_SQL` |
| `daily_measurement_funnel` | `store_id, d` | `MeasurementTicket` + `SaleOrder` | `POS_MEASUREMENT_FUNNEL_SQL` |
| `daily_customer_segments` | `store_id, d` | `SaleOrder` (new vs returning) | `POS_CUSTOMER_SEGMENTS_SQL` |
| `monthly_quality_returns` | `store_id, year_month` | `ReturnSaleOrder` + `SupplierWarranty` | `POS_QUALITY_RETURNS_SQL` |
| `monthly_inventory_sku` | `store_id, year_month, product_id` | `SaleOrderItem` + `StockItem` + `Product` | `POS_INVENTORY_SKU_SQL` |
| `daily_payment_methods` | `store_id, d, method_name` | `PaymentOrder` + `PaymentMethod` | `POS_PAYMENT_METHODS_SQL` |
| `daily_pos_sessions` | `store_id, d, session_id` | `PosSession` + `PosSessionStaff` | `POS_POS_SESSION_SQL` |
| `monthly_inventory_ageing` | `store_id, year_month, product_id, age_bucket` | `StockHistory` + `Warehouse` | `POS_INVENTORY_AGEING_SQL` |
| `monthly_return_reasons` | `store_id, year_month, reason` | `ReturnSaleOrderItem` + `ReturnSaleOrder` | `POS_RETURN_REASONS_SQL` |
| `customer_rfm_snapshot` | `customer_id, store_id` | `SaleOrder` (RFM) | `POS_CUSTOMER_RFM_SQL` |
| `monthly_funnel_steps` | `store_id, year_month, step_index` | `SaleOrder` + `MeasurementTicket` + `PaymentOrder` | `POS_FUNNEL_STEPS_SQL` |
| `monthly_customer_retention` | `store_id, year_month` | `SaleOrder` (set-diff) | `POS_CUSTOMER_RETENTION_SQL` |
| `monthly_targets` | `store_id, year_month` | Nhập tay / import | `POS_TARGETS_SQL` |
| `holidays` | `d` | Nhập tay / import | `POS_HOLIDAYS_SQL` |
| `daily_ratings` | `store_id, d` | ZnsDb (CSAT thật) | ZNS sync |
| `monthly_csat` | `store_id, year_month` | ZnsDb (CSAT thật) | ZNS sync |
| `monthly_store_leaderboard` | `store_id, year_month` | **Derived** (tự tính) | — |
| `monthly_csat_store` | `store_id, year_month` | **Derived** (tự tính) | — |

---

## 3. Zone Finance — Tài chính

### 3.1 Doanh thu (Revenue)

| KPI | Công thức | Nguồn |
|-----|-----------|-------|
| **Total Revenue** | `SUM(revenue_net)` từ `daily_sales_finance` trong kỳ `[d0, d1]` | `SaleOrder.NeedPayAmount` |
| **Revenue Trend %** | `(rev_current - rev_prev) / rev_prev × 100` | So sánh kỳ trước cùng độ dài |

**POS SQL** — `SaleOrder`:
```sql
-- revenue_net = SUM(SaleOrder.NeedPayAmount) theo ngày CompleteAt
SELECT source_store_id, DATE(o."CompleteAt" AT TIME ZONE 'Asia/Ho_Chi_Minh') AS d,
       SUM(o."NeedPayAmount") AS revenue_net
FROM "SaleOrder" o
WHERE o."DeleteAt" IS NULL AND o."CompleteAt" IS NOT NULL
GROUP BY source_store_id, d
```

### 3.2 Biên lợi nhuận gộp (GPM)

| KPI | Công thức | Nguồn |
|-----|-----------|-------|
| **GPM %** | `SUM(gross_profit) / SUM(revenue_net) × 100` | `daily_sales_finance` |
| **gross_profit** | `revenue_net - cogs_amount` | Tính từ `SaleOrderItem.SubTotalCostPrice` |

**POS SQL** — `SaleOrderItem`:
```sql
-- cogs_amount = SUM(SaleOrderItem.SubTotalCostPrice) theo SaleOrder
-- gross_profit = revenue_net - cogs_amount
```

### 3.3 NPM (Net Profit Margin) — Proxy

| KPI | Công thức | Nguồn |
|-----|-----------|-------|
| **NPM %** | `(revenue - cogs - opex_proxy) / revenue × 100` | `daily_sales_finance` |
| **opex_proxy** | `revenue × EDP_OPEX_PROXY_PCT` (mặc định 12%) | Cấu hình env |

### 3.4 ATV (Average Transaction Value)

| KPI | Công thức |
|-----|-----------|
| **ATV** | `SUM(revenue_net) / SUM(orders_n)` |

### 3.5 Revenue per Staff

| KPI | Công thức |
|-----|-----------|
| **Rev/Staff** | `Tổng doanh thu kỳ / SUM(stores.staff_count)` |
| **Mặc định** | `staff_count = 12` nếu chưa có dữ liệu |

---

## 4. Zone Customer — Khách hàng

### 4.1 Churn Rate (Proxy)

| KPI | Công thức | Nguồn |
|-----|-----------|-------|
| **Churn %** | `(1 - tỷ_lệ_repeat) × 100` | `daily_store_signals.churn_rate_pct` |

**POS SQL logic:**
```sql
-- Proxy: đơn không phải lần mua lặp lại
-- repeat = KH có đơn hoàn tất trước đó (SaleOrder.CompleteAt < current)
-- churn_rate_pct = 100 × (1 - repeat_count / total_orders)
```

### 4.2 UPT (Units Per Transaction)

| KPI | Công thức | Nguồn |
|-----|-----------|-------|
| **UPT** | `SUM(units_sold) / SUM(orders_n)` | `daily_sales_finance` hoặc `daily_store_signals` |

**POS:** `SUM(SaleOrderItem.Quantity) / COUNT(DISTINCT SaleOrder.Id)`

### 4.3 Remake Rate

| KPI | Công thức | Nguồn |
|-----|-----------|-------|
| **Remake %** | `SUM(remake_orders_n) / SUM(orders_n) × 100` | `daily_sales_finance` |

**POS logic:** Đơn có `MeasurementTicket` gắn cùng `CustomerId` + `SiteId` trong ±14 ngày trước `CompleteAt` → coi là remake/refit.

### 4.4 Customer Segments

| Segment | Công thức |
|---------|-----------|
| **Khách mới** | `CustomerId` không có `SaleOrder.CompleteAt` nào trước đó |
| **Khách quay lại** | `CustomerId` có ít nhất 1 đơn hoàn tất trước |
| **Khách ngủ đông** | `inactive_customers_n` (hiện = 0, cần CRM) |

### 4.5 Customer Retention (Set-diff)

| KPI | Công thức | Nguồn |
|-----|-----------|-------|
| **Retention %** | `retained / customers_prev × 100` | `monthly_customer_retention` |
| **Churn %** | `churned / customers_prev × 100` | `monthly_customer_retention` |

**POS SQL logic:**
```
customers_prev = KH có đơn tháng M-1
retained       = KH có đơn cả tháng M-1 VÀ M
new_acquired   = KH có đơn tháng M nhưng KHÔNG có tháng M-1
churned        = KH có đơn tháng M-1 nhưng KHÔNG có tháng M
```

### 4.6 RFM Segmentation

| Segment | Điều kiện |
|---------|-----------|
| **Champion** | recency ≤ 30 ngày AND frequency ≥ 3 |
| **Loyal** | recency ≤ 60 ngày AND frequency ≥ 2 |
| **At-Risk** | recency ≤ 120 ngày |
| **Hibernating** | recency ≤ 365 ngày |
| **Lost** | recency > 365 ngày |

**POS:** `recency = NOW() - MAX(SaleOrder.CompleteAt)`, `frequency = COUNT(DISTINCT SaleOrder.Id)`, `monetary = SUM(NeedPayAmount)`

---

## 5. Zone Inventory — Tồn kho

### 5.1 Dead Stock %

| KPI | Công thức | Nguồn |
|-----|-----------|-------|
| **Dead Stock %** | `COUNT(qty ≤ 0 OR is_return) / COUNT(*) × 100` | `monthly_inventory` ← `StockHistory` |

**POS SQL:**
```sql
-- Proxy từ StockHistory: tỷ lệ giao dịch xuất kho ≤ 0 hoặc return
FROM "StockHistory" h
JOIN "Warehouse" w ON w."Id" = h."WarehouseId"
```

### 5.2 Stock Cover Days

| KPI | Công thức |
|-----|-----------|
| **Stock Cover** | `AVG(EndStock) / AVG(ABS(Quantity))` ngày |
| **Cap** | Tối đa 3650 ngày |

### 5.3 GMROI (Gross Margin Return on Inventory)

| KPI | Công thức | Nguồn |
|-----|-----------|-------|
| **GMROI** | `SUM(gross_profit) / SUM(inventory_value)` | `monthly_inventory_sku` |

### 5.4 OOS (Out of Stock) %

| KPI | Công thức |
|-----|-----------|
| **OOS %** | `COUNT(stock_units ≤ 0 AND sold_units > 0) / COUNT(*) × 100` |

### 5.5 STR (Sell-Through Rate)

| KPI | Công thức |
|-----|-----------|
| **STR %** | `SUM(sold_units) / (SUM(sold_units) + SUM(stock_units)) × 100` |

### 5.6 Inventory Ageing

| Bucket | Điều kiện |
|--------|-----------|
| < 30 ngày | `age_days ≤ 30` |
| 31–90 ngày | `30 < age_days ≤ 90` |
| 91–180 ngày | `90 < age_days ≤ 180` |
| > 180 ngày | `age_days > 180` |

**POS:** `age_days = EXTRACT(day FROM NOW() - StockItem.InboundAt)`

### 5.7 Dead Stock (SKU-level)

| KPI | Công thức |
|-----|-----------|
| **Dead Stock SKU** | `sold_units = 0 AND age_days ≥ threshold` (mặc định 90 ngày) |

---

## 6. Zone Goal — Mục tiêu KPI

### 6.1 Target Achievement

| KPI | Công thức | Nguồn |
|-----|-----------|-------|
| **% Target** | `SUM(actual_revenue) / SUM(gt_weekday + gt_weekend + gt_holiday) × 100` | `monthly_targets` |
| **Coverage** | `stores_có_target / tổng_stores × 100` | Kiểm tra `monthly_targets` có record |

---

## 7. Sales & Marketing

### 7.1 Conversion Funnel (5 bước)

| Step | Nguồn | Proxy nếu thiếu |
|------|-------|-----------------|
| 1. Walk-in | — | `MAX(MeasurementTicket, orders × 1.6)` |
| 2. Khám mắt | `MeasurementTicket` | `orders × 1.4` |
| 3. Tạo giỏ | — | `orders × 1.15` |
| 4. Đơn hoàn tất | `SaleOrder (CompleteAt)` | — |
| 5. Thanh toán | `PaymentOrder` | `= orders` |

| KPI | Công thức |
|-----|-----------|
| **Conversion %** | `completed_orders / measurement_tickets × 100` |
| **Dropoff %** | `(prev_step - current_step) / prev_step × 100` |

### 7.2 Channel Mix

| KPI | Công thức | Nguồn |
|-----|-----------|-------|
| **Channel %** | `SUM(revenue_net) theo channel / tổng revenue × 100` | `daily_channel_sales` |

**POS:** `SaleChannel.Name`, `EcomSource.ShopName`, fallback `'Offline/POS'`

### 7.3 Campaign Performance

| KPI | Công thức | Nguồn |
|-----|-----------|-------|
| **Campaign Revenue** | `SUM(revenue_net)` per campaign | `daily_campaign_sales` |
| **Discount** | `SUM(discount_amount)` | `SaleOrder.PromotionDiscountAmount` |

**POS:** `PromotionCampaignSaleOrder` → `PromotionCampaign`; fallback theo channel nếu không có campaign.

---

## 8. Quality & CLV

### 8.1 CSAT (Customer Satisfaction)

| Nguồn | Công thức | Khi nào dùng |
|-------|-----------|--------------|
| **Real** (ZnsDb) | `AVG(score) × 20` (scale 0–100) | Khi có `ZNS_PG_DSN` |
| **Proxy** | `5 - defect_rate × 8` (scale 1–5) | Fallback khi không có ZNS |

`defect_rate = (return_orders + warranty_cases) / total_orders`

### 8.2 Return/Warranty Quality

| KPI | Công thức | Nguồn POS |
|-----|-----------|-----------|
| **Tỷ lệ đổi trả** | `(return_orders + warranty_cases) / orders × 100` | `ReturnSaleOrder` + `SupplierWarranty` |
| **Return Amount** | `SUM(ReturnSaleOrder.NeedPayAmount)` | `ReturnSaleOrder` |

### 8.3 CLV (Customer Lifetime Value)

| KPI | Công thức |
|-----|-----------|
| **CLV TB** | `SUM(revenue) / COUNT(DISTINCT customers có giao dịch)` |

### 8.4 Cohort Retention

| KPI | Công thức |
|-----|-----------|
| **Cohort size** | `SUM(new_customers_n)` tháng cohort |
| **Retention M+n** | `base_retention × decay[n]` |
| **decay** | `[1.0, 0.62, 0.42, 0.31, 0.24, 0.18]` |

---

## 9. Bảng Derived

Được tính tự động sau mỗi POS sync thành công (`_populate_derived_tables`):

### 9.1 `monthly_store_leaderboard`

```
revenue_net     = SUM(daily_sales_finance.revenue_net) GROUP BY store, SUBSTR(d,1,7)
orders_n        = SUM(daily_sales_finance.orders_n)
revenue_growth  = (rev_current - rev_prev_month) / rev_prev_month × 100
conv_rate       = completed_orders / measurement_tickets × 100
atv             = revenue / orders
upt             = units / orders
remake_rate     = remake_orders / orders × 100
rev_per_staff   = revenue / staff_count
```

Rank: `revenue_rank`, `conv_rank`, `atv_rank`, `remake_rank` (ASC), `rps_rank` — per `year_month`.

### 9.2 `monthly_csat_store`

| Trường hợp | Công thức |
|-------------|-----------|
| **Có daily_ratings** | `avg_score = SUM(avg_score × ratings_count) / SUM(ratings_count)` |
| | `pct_4_5_star = SUM(score_4 + score_5) / SUM(ratings_count) × 100` |
| **Fallback (proxy)** | `score = MAX(1, MIN(5, (1 - returns/orders) × 5))` |

Status label:
- `< 5 ratings` → "Insufficient Data"
- `score ≥ 4.0` → "Good"
- `score ≥ 3.0` → "Warning"
- else → "Low"

---

## 10. Mapping POS Tables → SQL

### Bảng POS PostgreSQL được sử dụng

| POS Table | Dùng cho | Cột quan trọng |
|-----------|----------|----------------|
| `Site` | Stores, ID mapping | `Id`, `StoreName`, `Name`, `ProvinceCode`, `SiteGroupId` |
| `Province` | Regions | `Code`, `Name` |
| `SiteGroup` | Strategic zone | `Name` |
| `SaleOrder` | Revenue, Orders, Finance | `Id`, `SiteId`, `CustomerId`, `CompleteAt`, `NeedPayAmount`, `DiscountAmount` |
| `SaleOrderItem` | COGS, Units, SKU | `SaleOrderId`, `SubTotalCostPrice`, `Quantity`, `SubTotal`, `ProductId` |
| `MeasurementTicket` | Funnel, Remake | `Id`, `SiteId`, `CustomerId`, `IssueAt` |
| `StockHistory` | Inventory | `WarehouseId`, `ProductId`, `Quantity`, `EndStock`, `IsReturn`, `CostPrice` |
| `StockItem` | SKU inventory | `WarehouseId`, `ProductId`, `InboundAt`, `OutboundAt`, `DamageAt`, `CostPrice` |
| `Warehouse` | Store mapping | `Id`, `SiteId` |
| `Product` | Product info | `Id`, `Name`, `Code`, `ProductCategoryId`, `BrandId` |
| `ProductCategory` | Category | `Id`, `Name` |
| `Brand` | Brand | `Id`, `Name` |
| `SaleChannel` | Channel sales | `Id`, `Name` |
| `EcomSource` | E-commerce | `Id`, `ShopName` |
| `PromotionCampaign` | Campaigns | `Id`, `Name`, `Code` |
| `PromotionCampaignSaleOrder` | Campaign → Order link | `PromotionCampaignId`, `SaleOrderId` |
| `ReturnSaleOrder` | Returns | `Id`, `SiteId`, `CompleteAt`, `NeedPayAmount`, `Note` |
| `ReturnSaleOrderItem` | Return reasons | `ReturnSaleOrderId`, `Note`, `SubTotal` |
| `SupplierWarranty` | Warranty | `Id`, `SiteId`, `IssueAt`, `WarrantyReason` |
| `PaymentOrder` | Payment methods | `Id`, `SaleOrderId`, `PaymentMethodId`, `ActualAmount`, `PaidAmount` |
| `PaymentMethod` | Method names | `Id`, `Name` |
| `PosSession` | Sessions | `Id`, `SiteId`, `OpenAt`, `CloseAt` |
| `PosSessionStaff` | Staff mapping | `PosSessionId`, `StaffId` |
| `Customer` | Customer info | `Id`, `SiteId` |

### Soft-delete convention

Tất cả bảng POS dùng `"DeleteAt" IS NULL` để lọc bản ghi active.

### Timezone

- `CompleteAt` lưu dạng `TIMESTAMPTZ` (UTC).
- Convert sang local: `AT TIME ZONE '{SYNC_TZ}'` (mặc định `Asia/Ho_Chi_Minh`).
- Cắt ngày: `DATE(... AT TIME ZONE ...)`.

### Incremental sync

- `{SYNC_CUTOFF_UTC}`: thời điểm sync thành công gần nhất trừ `POS_SYNC_OVERLAP_DAYS` (mặc định 2).
- Lần đầu: lookback `POS_SYNC_INITIAL_LOOKBACK_DAYS` (mặc định 3650 ~ 10 năm).
- Upsert: `INSERT ... ON CONFLICT DO UPDATE` để idempotent.
