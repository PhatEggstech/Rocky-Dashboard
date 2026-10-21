---
title: Data Fields Validation — Tổng hợp trường dữ liệu dự án HMK BigData
created: 2026-05-19
author: AI-assisted (data platform)
status: pending_leader_review
purpose: Để leader validate tính đúng đắn, đầy đủ và nhất quán của các trường dữ liệu xuyên suốt pipeline
---

# DATA FIELDS VALIDATION — HMK BigData System

> **Mục đích**: Tài liệu này tổng hợp **toàn bộ trường dữ liệu**, **công thức tính toán**, và **quy tắc nghiệp vụ** xuyên suốt pipeline (Source → Bronze → Silver → Gold → EDP). Leader review để xác nhận tính đúng đắn trước khi go-live.

---

## Mục lục

1. [Tổng quan kiến trúc dữ liệu](#1-tổng-quan-kiến-trúc-dữ-liệu)
2. [Source → Bronze: Column Mapping](#2-source--bronze-column-mapping)
3. [Silver — Dimensions](#3-silver--dimensions)
4. [Silver — Fact Tables](#4-silver--fact-tables)
5. [Gold Layer](#5-gold-layer)
6. [EDP SQLite (Serving)](#6-edp-sqlite-serving)
7. [KPI Contract](#7-kpi-contract)
8. [Business Rules & Formulas](#8-business-rules--formulas)
9. [Data Contracts](#9-data-contracts)
10. [Leader Validation Checklist](#10-leader-validation-checklist)

---

## 1. Tổng quan kiến trúc dữ liệu

```
POS PostgreSQL (255 bảng, PascalCase, OLTP)
  ↓ extract.py (watermark, retry, UUID cast)
Bronze (21 bảng PG, snake_case, +metadata: _extracted_at, _source_system, _batch_id, d)
  ↓ Silver SQL scripts (dedup, join, aggregate)
Silver (7 dim + 16 fact tables, logic nghiệp vụ)
  ↓ Gold SQL scripts (UPSERT passthrough)
Gold (22 bảng, serving marts)
  ↓ pos_sync.py / warehouse pool
EDP SQLite / React Dashboard
```

| Layer | Số bảng | Grain | Ghi chú |
|-------|---------|-------|---------|
| Source (POS PG) | 255 | OLTP row | PascalCase, UUID PK, `DeleteAt` soft-delete |
| Bronze | 21 | 1:1 mirror | snake_case, +`_extracted_at`, `_source_system`, `_batch_id`, `d` |
| Silver | 23 | Aggregated | 7 dim + 16 fact (daily/monthly) |
| Gold | 22 | = Silver | Passthrough materialization |
| EDP SQLite | 22+ | = Gold | Local serving cho FastAPI |

---

## 2. Source → Bronze: Column Mapping

### 2.1 Metadata columns (thêm vào TẤT CẢ bảng Bronze)

| Field | Type | Mô tả |
|-------|------|--------|
| `_extracted_at` | TIMESTAMPTZ | Thời điểm extract |
| `_source_system` | TEXT | Luôn = `'pos_pg'` |
| `_batch_id` | TEXT | ID batch extract |
| `d` | DATE | Derived từ timestamp chính, TZ `Asia/Ho_Chi_Minh` |

### 2.2 Bảng `sale_order` (đơn bán — bảng trục chính)

| Source (POS PascalCase) | Bronze (snake_case) | Type | Ghi chú |
|-------------------------|---------------------|------|---------|
| `SaleOrder.Id` | `id` | UUID PK | |
| `SaleOrder.Code` | `code` | TEXT | Mã đơn |
| `SaleOrder.SiteId` | `site_id` | UUID | FK → site |
| `SaleOrder.CustomerId` | `customer_id` | UUID | FK → customer |
| `SaleOrder.StaffId` | `staff_id` | UUID | Nhân viên bán |
| `SaleOrder.RefractionistStaffId` | `refractionist_staff_id` | UUID | Nhân viên đo mắt |
| `SaleOrder.PosSessionId` | `pos_session_id` | UUID | FK → pos_session |
| `SaleOrder.StateId` | `state_id` | UUID | Trạng thái workflow |
| `SaleOrder.SaleChannelId` | `sale_channel_id` | UUID | Kênh bán |
| `SaleOrder.EcomSourceId` | `ecom_source_id` | UUID | Nguồn e-commerce |
| `SaleOrder.ExchangeParentId` | `exchange_parent_id` | UUID | Link đổi/remake |
| `SaleOrder.ProductAmount` | `total_amount` | DOUBLE PRECISION | Tổng trước giảm giá |
| `SaleOrder.DiscountAmount` | `discount_amount` | DOUBLE PRECISION | Giảm giá |
| `SaleOrder.TotalDiscountAmount` | `total_discount_amount` | DOUBLE PRECISION | Tổng giảm |
| `SaleOrder.PromotionDiscountAmount` | `promotion_discount_amount` | DOUBLE PRECISION | Giảm từ CTKM |
| `SaleOrder.NeedPayAmount` | `need_pay_amount` | DOUBLE PRECISION | **Doanh thu thuần (Revenue Net)** |
| `SaleOrder.NeedPayAmountIgnoreVat` | `need_pay_amount_ignore_vat` | DOUBLE PRECISION | DT trước VAT |
| `SaleOrder.VatAmount` | `vat_amount` | DOUBLE PRECISION | Thuế VAT |
| `SaleOrder.PaidAmount` | `paid_amount` | DOUBLE PRECISION | Đã thanh toán |
| `SaleOrder.CustomerPaid` | `customer_paid` | DOUBLE PRECISION | KH đã trả |
| `SaleOrder.SubTotalCostPrice` | `cost_amount` | DOUBLE PRECISION | **COGS (giá vốn)** |
| `SaleOrder.Quantity` | `quantity` | DOUBLE PRECISION | Số lượng SP |
| `SaleOrder.IssueAt` | `issue_at` | TIMESTAMPTZ | Ngày tạo đơn |
| `SaleOrder.SubmitAt` | `submit_at` | TIMESTAMPTZ | Ngày submit |
| `SaleOrder.CompleteAt` | `complete_at` | TIMESTAMPTZ | **Ngày hoàn tất (dùng ghi nhận DT)** |
| `SaleOrder.CancelAt` | `cancel_at` | TIMESTAMPTZ | Ngày hủy |
| `SaleOrder.DeleteAt` | `delete_at` | TIMESTAMPTZ | Soft delete |
| `SaleOrder.CreateAt` | `create_at` | TIMESTAMPTZ | |
| `SaleOrder.UpdateAt` | `update_at` | TIMESTAMPTZ | |
| _(derived)_ | `d` | DATE | `complete_at` → DATE (TZ Asia/HCM) |

### 2.3 Bảng `sale_order_item` (dòng hàng)

| Source | Bronze | Type | Ghi chú |
|--------|--------|------|---------|
| `SaleOrderItem.Id` | `id` | UUID PK | |
| `SaleOrderItem.SaleOrderId` | `sale_order_id` | UUID | FK → sale_order |
| `SaleOrderItem.ProductId` | `product_id` | UUID | FK → product |
| `SaleOrderItem.Quantity` | `quantity` | DOUBLE PRECISION | Số lượng |
| `SaleOrderItem.OriginalPrice` | `original_price` | DOUBLE PRECISION | Giá gốc |
| `SaleOrderItem.Price` | `price` | DOUBLE PRECISION | Giá bán |
| `SaleOrderItem.ActualPrice` | `actual_price` | DOUBLE PRECISION | Giá thực |
| `SaleOrderItem.DiscountPrice` | `discount_price` | DOUBLE PRECISION | Giá giảm |
| `SaleOrderItem.TotalDiscountAmount` | `discount_amount` | DOUBLE PRECISION | Tổng tiền giảm |
| `SaleOrderItem.PromotionDiscountAmount` | `promotion_discount_amount` | DOUBLE PRECISION | Giảm CTKM |
| `SaleOrderItem.SubTotal` | `total_amount` | DOUBLE PRECISION | Thành tiền |
| `SaleOrderItem.CostPrice` | `cost_price` | DOUBLE PRECISION | Giá vốn đơn vị |
| `SaleOrderItem.SubTotalCostPrice` | `cost_amount` | DOUBLE PRECISION | **COGS dòng hàng** |
| `SaleOrderItem.IsPromotionGift` | `is_promotion_gift` | BOOLEAN | Là quà tặng KM |
| `SaleOrderItem.PromotionCampaignItemId` | `promotion_campaign_item_id` | UUID | FK campaign item |

### 2.4 Bảng `customer`

| Source | Bronze | Type | Ghi chú |
|--------|--------|------|---------|
| `Customer.Id` | `id` | UUID PK | |
| `Customer.Code` | `code` | TEXT | |
| `Customer.Name` | `name` | TEXT | |
| `Customer.Phone` | `phone` | TEXT | |
| `Customer.Email` | `email` | TEXT | |
| `Customer.SiteId` | `site_id` | UUID | CH quản lý KH |
| `Customer.CompanyId` | `company_id` | UUID | |
| `Customer.CustomerGroupId` | `customer_group_id` | UUID | Nhóm KH |
| `Customer.MinCustomerGroupId` | `min_customer_group_id` | UUID | |
| `Customer.Gender` | `gender` | INTEGER | |
| `Customer.Birthday` | `date_of_birth` | TIMESTAMPTZ | |
| `Customer.ProvinceCode` | `province_code` | TEXT | |
| `Customer.DistrictCode` | `district_code` | TEXT | |
| `Customer.TotalSaleAmount` | `total_sale_amount` | DOUBLE PRECISION | Tổng DT tích lũy |
| `Customer.TotalSaleAmountIncludeReturnAmount` | `total_sale_amount_include_return` | DOUBLE PRECISION | DT kể cả trả |
| `Customer.CurrentDebtAmount` | `current_debt_amount` | DOUBLE PRECISION | Công nợ hiện tại |
| `Customer.LastTransactionAt` | `last_transaction_at` | TIMESTAMPTZ | Lần mua cuối |

### 2.5 Bảng `product`

| Source | Bronze | Type | Ghi chú |
|--------|--------|------|---------|
| `Product.Id` | `id` | UUID PK | |
| `Product.Code` | `code` | TEXT | |
| `Product.Name` | `name` | TEXT | |
| `Product.Fullname` | `fullname` | TEXT | |
| `Product.Type` | `type` | INTEGER | Loại SP |
| `Product.ProductCategoryId` | `category_id` | UUID | |
| `Product.BrandId` | `brand_id` | UUID | |
| `Product.MasterUnitId` | `master_unit_id` | UUID | |
| `Product.UnitName` | `unit_name` | TEXT | |
| `Product.CostPrice` | `cost_price` | DOUBLE PRECISION | Giá vốn |
| `Product.SalePrice` | `price` | DOUBLE PRECISION | Giá bán |
| `Product.SalePriceIgnoreTax` | `price_ignore_tax` | DOUBLE PRECISION | Giá trước thuế |
| `Product.StockQuantity` | `stock_quantity` | DOUBLE PRECISION | Tồn snapshot |
| `Product.CanSaleOnPos` | `can_sale_on_pos` | BOOLEAN | |
| `Product.State` | `state` | INTEGER | |

### 2.6 Bảng `stock_item` (tồn kho vật lý)

| Source | Bronze | Type | Ghi chú |
|--------|--------|------|---------|
| `StockItem.Id` | `id` | UUID PK | 1 row = 1 đơn vị vật lý |
| `StockItem.ProductId` | `product_id` | UUID | |
| `StockItem.WarehouseId` | `warehouse_id` | UUID | |
| `StockItem.CostPrice` | `cost_amount` | DOUBLE PRECISION | Giá vốn đơn vị |
| `StockItem.InboundAt` | `inbound_at` | TIMESTAMPTZ | Ngày nhập |
| `StockItem.OutboundAt` | `outbound_at` | TIMESTAMPTZ | Ngày xuất |
| `StockItem.DamageAt` | `damage_at` | TIMESTAMPTZ | Ngày hỏng |
| `StockItem.StateId` | `state_id` | UUID | |

### 2.7 Các bảng Bronze khác (tóm tắt)

| Bảng | Số trường chính | Grain | Timestamp cho `d` |
|------|-----------------|-------|-------------------|
| `site` | 10 | 1/site | `create_at` |
| `stock_history` | 11 | 1/movement | `create_at` |
| `measurement_ticket` | 8 | 1/ticket | `issue_at` |
| `cut_ticket` | 10 | 1/ticket | `complete_at` |
| `return_sale_order` | 11 | 1/return | `complete_at` |
| `return_sale_order_item` | 7 | 1/line | _(theo header)_ |
| `promotion_campaign_sale_order` | 4 | bridge | — |
| `pos_session` | 9 | 1/session | `open_at` |
| `warehouse` | 9 | 1/warehouse | — |
| `product_category` | 6 | 1/category | — |
| `brand` | 3 | 1/brand | — |
| `sale_channel` | 4 | 1/channel | — |
| `ecom_source` | 5 | 1/source | — |
| `promotion_campaign` | 10 | 1/campaign | — |
| `measurement_ticket_sale_order_item` | 4 | bridge | — |
| `supplier_warranty` | 10 | 1/warranty | `issue_at` |

---

## 3. Silver — Dimensions

### 3.1 `dim_store`

| Field | Type | Source / Transform | Validate |
|-------|------|-------------------|----------|
| `store_id` | INTEGER PK | `ROW_NUMBER() OVER (ORDER BY code, name, id)` | ⚠️ Stable synthetic ID — verify không đổi khi thêm store mới |
| `source_site_id` | UUID UNIQUE | `bronze.site.id` | |
| `name` / `code` | TEXT | Direct | |
| `region_id` | INTEGER | NULL (pending dim_region) | ❓ Cần bổ sung mapping region |
| `is_active` | BOOLEAN | `delete_at IS NULL AND state = 1` | |
| `staff_count` | INTEGER | 0 (placeholder) | ❓ Nguồn headcount thực tế? |
| `strategic_zone` | TEXT | NULL | ❓ Quy tắc phân zone? |
| `pos_site_guid` | TEXT | `site.id::text` | |

### 3.2 `dim_product`

| Field | Type | Source / Transform | Validate |
|-------|------|-------------------|----------|
| `product_id` | UUID PK | `bronze.product.id` | |
| `code` / `name` / `fullname` | TEXT | Direct | |
| `category_id` | UUID | `bronze.product.category_id` | |
| `category_name` | TEXT | Denormalized từ `dim_category.name` | |
| `brand_id` | UUID | `bronze.product.brand_id` | |
| `brand_name` | TEXT | Denormalized từ `dim_brand.name` | |
| `type` | INTEGER | Product type code | |
| `cost_price` / `sale_price` | DOUBLE PRECISION | Direct | |
| `is_active` | BOOLEAN | `delete_at IS NULL AND state active` | |

### 3.3 `dim_category`

| Field | Type | Transform | Validate |
|-------|------|-----------|----------|
| `category_id` | UUID PK | Direct | |
| `code` / `name` | TEXT | Direct | |
| `parent_id` | UUID | Hierarchy link | |
| `level` | INTEGER | `hierarchy_level` | |
| `root_id` | UUID | Recursive CTE → top parent | ⚠️ Verify CTE xử lý đúng cycle |
| `root_name` | TEXT | Name of root | |
| `is_active` | BOOLEAN | `delete_at IS NULL` | |

### 3.4 `dim_channel`

| Field | Type | Values | Validate |
|-------|------|--------|----------|
| `channel_key` | TEXT PK | `'offline'`, `'web'`, `'shopee'`, `'tiktok_shop'`, `'lazada'`, `'tiki'`, `'other'` | |
| `label` | TEXT | Display name tiếng Việt | |
| `source_kind` | TEXT | `'sale_channel'` / `'ecom_source'` / `'unknown'` | |
| `sort_order` | INTEGER | 1-99 | |

### 3.5 `dim_brand` / `dim_warehouse` / `dim_campaign`

| Dimension | PK | Nguồn | Active check |
|-----------|-----|-------|-------------|
| `dim_brand` | `brand_id` UUID | `bronze.brand` | `delete_at IS NULL` |
| `dim_warehouse` | `warehouse_id` UUID | `bronze.warehouse` | `delete_at IS NULL AND state = 1` |
| `dim_campaign` | `campaign_id` UUID | `bronze.promotion_campaign` | `is_active` field |

---

## 4. Silver — Fact Tables

### 4.1 `daily_sales_finance` — Grain: (store_id, d)

| Field | Type | Formula | Validate |
|-------|------|---------|----------|
| `store_id` | INTEGER FK | Join via `dim_store.source_site_id` | |
| `d` | DATE | Order date (TZ HCM) | |
| `orders_n` | DOUBLE PRECISION | `COUNT(DISTINCT sale_order.id) WHERE complete_at IS NOT NULL AND delete_at IS NULL` | ⚠️ Chỉ đơn hoàn tất |
| `revenue_net` | DOUBLE PRECISION | `SUM(need_pay_amount)` | **KPI chính** |
| `cogs_amount` | DOUBLE PRECISION | `SUM(sale_order_item.cost_amount)` | ⚠️ Lấy từ item, không từ header |
| `gross_profit` | DOUBLE PRECISION | `revenue_net - cogs_amount` | |
| `units_sold` | DOUBLE PRECISION | `SUM(sale_order_item.quantity)` | |
| `unique_customers_n` | DOUBLE PRECISION | `COUNT(DISTINCT customer_id)` | |
| `remake_orders_n` | DOUBLE PRECISION | `COUNT(DISTINCT id) WHERE exchange_parent_id IS NOT NULL` | |

### 4.2 `daily_channel_sales` — Grain: (store_id, channel_key, d)

| Field | Type | Formula | Validate |
|-------|------|---------|----------|
| `store_id` | INTEGER FK | | |
| `channel_key` | TEXT | Mapping logic: `ecom_source.type` → tên kênh, fallback `sale_channel.name`, else `'offline'` | ⚠️ Priority: ecom > sale_channel > default |
| `d` | DATE | | |
| `orders_n` | DOUBLE PRECISION | `COUNT(DISTINCT order_id)` | |
| `revenue_net` | DOUBLE PRECISION | `SUM(need_pay_amount)` | |
| `units_sold` | DOUBLE PRECISION | `SUM(line item quantity)` | |
| `cogs_amount` | DOUBLE PRECISION | `SUM(order cost_amount)` | |

**Channel mapping detail:**

| `ecom_source.type` | `channel_key` |
|---------------------|---------------|
| 1 | `shopee` |
| 2 | `lazada` |
| 3 | `tiki` |
| 4 | `tiktok_shop` |
| NULL + sale_channel = 'web' | `web` |
| NULL + no ecom | `offline` |
| Other | `other` |

### 4.3 `daily_campaign_sales` — Grain: (campaign_id, d)

| Field | Type | Formula | Validate |
|-------|------|---------|----------|
| `campaign_id` | UUID FK | Từ `promotion_campaign_sale_order` bridge | |
| `d` | DATE | | |
| `orders_n` | DOUBLE PRECISION | Order count in campaign | |
| `revenue_net` | DOUBLE PRECISION | Revenue attributed | |
| `promotion_discount` | DOUBLE PRECISION | Discount amount (proxy CAC) | |
| `customers_n` | DOUBLE PRECISION | Unique customers | |
| `new_customers_n` | DOUBLE PRECISION | First-time buyers during campaign | ⚠️ Verify logic "first-time" |

### 4.4 `daily_measurement_funnel` — Grain: (store_id, d)

| Field | Type | Formula | Validate |
|-------|------|---------|----------|
| `store_id` | INTEGER FK | | |
| `d` | DATE | | |
| `measurement_tickets_n` | DOUBLE PRECISION | COUNT measurement tickets (walk-ins) | |
| `completed_orders_n` | DOUBLE PRECISION | Orders linked via bridge `measurement_ticket_sale_order_item` | ⚠️ Bridge join path |
| `revenue_net` | DOUBLE PRECISION | Revenue from those orders | |

### 4.5 `daily_customer_segments` — Grain: (store_id, d, segment_key)

| Field | Type | Formula | Validate |
|-------|------|---------|----------|
| `store_id` | INTEGER FK | | |
| `d` | DATE | | |
| `segment_key` | TEXT | `'new'` / `'returning'` / `'inactive'` | |
| `customers_n` | DOUBLE PRECISION | Count per segment | |
| `revenue_net` | DOUBLE PRECISION | Revenue per segment | |
| `orders_n` | DOUBLE PRECISION | Orders per segment | |

**Segment definitions:**

| Segment | Định nghĩa |
|---------|------------|
| `new` | Đơn đầu tiên ever = ngày d |
| `returning` | Có đơn trong 180 ngày trước d |
| `inactive` | Không phải new, không phải returning |

### 4.6 `daily_store_signals` — Grain: (store_id, d)

| Field | Type | Formula | Validate |
|-------|------|---------|----------|
| `store_id` | INTEGER FK | | |
| `d` | DATE | | |
| `orders_n` | DOUBLE PRECISION | Daily order count | |
| `units_n` | DOUBLE PRECISION | Daily units sold | |
| `churn_rate_pct` | DOUBLE PRECISION | Proxy churn signal | ⚠️ Algorithm churn cần clarify |

### 4.7 `monthly_inventory` — Grain: (store_id, year_month)

| Field | Type | Formula | Validate |
|-------|------|---------|----------|
| `store_id` | INTEGER FK | Via `dim_warehouse` → `dim_store` | |
| `year_month` | TEXT `'YYYY-MM'` | | |
| `dead_stock_pct` | DOUBLE PRECISION | `100 × units_inbound_>90d_ago / total_active_units` | ⚠️ Threshold 90 ngày có phù hợp? |
| `stock_cover_days` | DOUBLE PRECISION | `active_units / (units_sold_per_day)` | ⚠️ Denominator = sold/30 days |

### 4.8 `monthly_inventory_sku` — Grain: (store_id, year_month, product_id)

| Field | Type | Formula | Validate |
|-------|------|---------|----------|
| `store_id` | INTEGER FK | | |
| `year_month` | TEXT | | |
| `product_id` | UUID | | |
| `on_hand_units` | DOUBLE PRECISION | Active StockItems at EOM | |
| `on_hand_value` | DOUBLE PRECISION | `SUM(cost_amount)` of active items | |
| `units_sold` | DOUBLE PRECISION | Units sold in month | |
| `revenue_net` | DOUBLE PRECISION | Revenue from product in month | |
| `cogs_amount` | DOUBLE PRECISION | COGS from product in month | |
| `sell_through_pct` | DOUBLE PRECISION | `100 × units_sold / (on_hand + units_sold)` | |

### 4.9 `monthly_inventory_ageing` — Grain: (store_id, year_month, bucket)

| Field | Type | Formula | Validate |
|-------|------|---------|----------|
| `bucket` | TEXT | `'0-30'`, `'31-60'`, `'61-90'`, `'91-180'`, `'180+'` | |
| `units_n` | DOUBLE PRECISION | Unit count per bucket | |
| `value_amt` | DOUBLE PRECISION | Cost value per bucket | |

**Bucket = days since `inbound_at` to End-of-Month**

### 4.10 `monthly_abc_sku` — Grain: (year_month, product_id)

| Field | Type | Formula | Validate |
|-------|------|---------|----------|
| `revenue_net` | DOUBLE PRECISION | SKU monthly revenue | |
| `units_sold` | DOUBLE PRECISION | SKU monthly units | |
| `cum_revenue_pct` | DOUBLE PRECISION | Cumulative % descending | |
| `abc_class` | TEXT | A (cum ≤70%), B (≤90%), C (rest) | ⚠️ Threshold industry-standard? |

### 4.11 `monthly_gmroi_category` — Grain: (year_month, category_id)

| Field | Type | Formula | Validate |
|-------|------|---------|----------|
| `category_id` | UUID | Root category | |
| `revenue_net` | DOUBLE PRECISION | Category revenue | |
| `cogs_amount` | DOUBLE PRECISION | Category COGS | |
| `gross_profit` | DOUBLE PRECISION | `revenue_net - cogs_amount` | |
| `avg_inventory_value` | DOUBLE PRECISION | Average `on_hand_value` during month | ⚠️ Cách tính average: BOM+EOM/2 hay daily avg? |
| `gmroi` | DOUBLE PRECISION | `gross_profit / avg_inventory_value` | |

### 4.12 `monthly_quality_returns` — Grain: (store_id, year_month)

| Field | Type | Formula | Validate |
|-------|------|---------|----------|
| `return_orders_n` | DOUBLE PRECISION | COUNT return orders | |
| `return_amount` | DOUBLE PRECISION | SUM `return_sale_order.need_pay_amount` | |
| `warranty_cases_n` | DOUBLE PRECISION | COUNT `supplier_warranty` | |
| `top_reason` | TEXT | MODE of return reason text | ⚠️ Keyword extraction hay full text? |

### 4.13 `monthly_return_reasons` — Grain: (year_month, reason_key)

| Field | Type | Formula | Validate |
|-------|------|---------|----------|
| `reason_key` | TEXT | Parsed from `return_sale_order.reason` | ⚠️ Logic parse cần document |
| `count_n` | DOUBLE PRECISION | Occurrences | |
| `amount` | DOUBLE PRECISION | Total return amount | |
| `cum_pct` | DOUBLE PRECISION | Cumulative % (Pareto) | |

### 4.14 `monthly_customer_retention` — Grain: (store_id, year_month)

| Field | Type | Formula | Validate |
|-------|------|---------|----------|
| `customers_prev` | DOUBLE PRECISION | Unique customers previous month | |
| `customers_curr` | DOUBLE PRECISION | Unique customers current month | |
| `retained` | DOUBLE PRECISION | `prev ∩ curr` | |
| `new_acquired` | DOUBLE PRECISION | `curr \ prev` | |
| `churned` | DOUBLE PRECISION | `prev \ curr` | |
| `retention_rate` | DOUBLE PRECISION | `retained / customers_prev` | ⚠️ Div-by-zero khi prev=0? |
| `churn_rate` | DOUBLE PRECISION | `churned / customers_prev` | |

### 4.15 `monthly_cohort_retention` — Grain: (cohort_ym, period_idx)

| Field | Type | Formula | Validate |
|-------|------|---------|----------|
| `cohort_ym` | TEXT | Month of first purchase | |
| `period_idx` | INTEGER | 0..N months after cohort | |
| `cohort_size` | DOUBLE PRECISION | Customers in cohort | |
| `active_n` | DOUBLE PRECISION | Still active at period | |
| `retention_pct` | DOUBLE PRECISION | `active_n / cohort_size` | |

### 4.16 `customer_rfm_snapshot` — Grain: (snapshot_date, customer_id)

| Field | Type | Formula | Validate |
|-------|------|---------|----------|
| `snapshot_date` | DATE | Snapshot point | |
| `customer_id` | UUID | | |
| `store_id` | INTEGER FK | Primary store (most orders) | |
| `recency_days` | DOUBLE PRECISION | Days since last order | |
| `frequency_n` | DOUBLE PRECISION | Order count in 12 months | |
| `monetary` | DOUBLE PRECISION | Total spend in 12 months | |
| `r_score` / `f_score` / `m_score` | INTEGER (1-5) | Quintile scores | |
| `rfm_segment` | TEXT | Rule-based (Champions, Loyal, At Risk, Hibernating...) | ⚠️ Bảng segment rules? |

---

## 5. Gold Layer

Gold = **passthrough materialization** của Silver. Pattern SQL:

```sql
INSERT INTO gold.<table> (..., _updated_at)
SELECT ..., NOW() FROM silver.<table>
WHERE d >= '{START_DATE}'
ON CONFLICT (...) DO UPDATE SET ...;
```

### Khác biệt Gold vs Silver

| Gold Table | Khác biệt so với Silver |
|------------|------------------------|
| `gold.stores` | Thêm `pos_site_id` (UUID), bỏ `source_warehouse_id` |
| `gold.dim_channel` | Bỏ `sale_channel_id`, `ecom_source_id` |
| Tất cả bảng khác | **Cùng cấu trúc** với Silver |

---

## 6. EDP SQLite (Serving)

SQLite schema trong `executive_dashboard/app/db.py` — phục vụ FastAPI dashboard. Dưới đây là mapping so với Gold/Silver.

### 6.1 Bảng mapping Gold → SQLite

| Gold/Silver Table | SQLite Table | Khác biệt |
|-------------------|-------------|------------|
| `gold.stores` | `stores` | Thêm `staff_count`, `strategic_zone`, `pos_site_id`, `pos_site_guid` |
| `gold.daily_sales_finance` | `daily_sales_finance` | Cùng fields |
| `gold.daily_store_signals` | `daily_store_signals` | Cùng fields |
| `gold.monthly_inventory` | `monthly_inventory` | Cùng fields |
| `gold.monthly_customer_retention` | `monthly_customer_retention` | Cùng fields |
| `gold.daily_channel_sales` | `daily_channel_sales` | SQLite: `channel_name` (vs Gold: `channel_key`); thêm `discount_amount` |
| `gold.daily_campaign_sales` | `daily_campaign_sales` | SQLite: thêm `store_id`, `campaign_name`, `discount_amount`; bỏ `customers_n`, `new_customers_n` |
| `gold.daily_measurement_funnel` | `daily_measurement_funnel` | Cùng fields |
| `gold.daily_customer_segments` | `daily_customer_segments` | SQLite: flatten thành `new_customers_n`, `returning_customers_n`, `inactive_customers_n`, `revenue_new`, `revenue_returning` |
| `gold.monthly_quality_returns` | `monthly_quality_returns` | Cùng fields |
| `gold.monthly_inventory_sku` | `monthly_inventory_sku` | SQLite: thêm `product_name`, `category_name`, `brand_name`, `age_days`; rename `on_hand_value` → `inventory_value`, `on_hand_units` → `stock_units` |
| `gold.monthly_inventory_ageing` | `monthly_inventory_ageing` | SQLite: thêm `product_id`, `age_days`; rename `bucket` → `age_bucket` |
| `gold.monthly_return_reasons` | `monthly_return_reasons` | SQLite: thêm `store_id`; rename `reason_key` → `reason`, `count_n` → `count` |
| `gold.customer_rfm_snapshot` | `customer_rfm_snapshot` | SQLite: bỏ `snapshot_date`, `r/f/m_score`; thêm `last_transaction_at`, `segment` (vs `rfm_segment`) |
| _(không có Gold)_ | `monthly_brand_category_metrics` | Mới — aggregate by category+brand |
| _(không có Gold)_ | `daily_payment_methods` | Mới — payment method breakdown |
| _(không có Gold)_ | `daily_pos_sessions` | Mới — POS session productivity |
| _(không có Gold)_ | `monthly_funnel_steps` | Mới — funnel visualization |
| _(không có Gold)_ | `daily_ratings` | Mới — CSAT daily (từ ZNS) |
| _(không có Gold)_ | `monthly_csat` | Mới — CSAT monthly |

### 6.2 Bảng chỉ có trong SQLite (support/operational)

| Table | Fields | Mục đích |
|-------|--------|----------|
| `regions` | `id`, `name` | Vùng quản lý |
| `holidays` | `d`, `label` | Calendar ngày lễ (tính target) |
| `monthly_targets` | `store_id`, `year_month`, `gt_weekday`, `gt_weekend`, `gt_holiday` | Chỉ tiêu doanh thu |
| `daily_revenue` | `store_id`, `d`, `amount` | Legacy revenue (phase-out) |
| `sync_state` | `key`, `value`, `updated_at_utc` | Trạng thái sync |
| `sync_runs` | 12 fields | Log sync runs |

---

## 7. KPI Contract

Từ `executive_dashboard/app/kpi_contract.py`:

### 7.1 KPI theo vai trò

| Vai trò | KPIs bắt buộc |
|---------|---------------|
| **CEO** (toàn chuỗi) | `gmv_net`, `orders`, `aov`, `gross_margin_pct`, `net_margin_pct`, `repeat_customer_rate_pct`, `new_customers`, `inventory_turnover`, `stockout_risk_sku_n`, `campaign_revenue_share_pct` |
| **RSM** (theo region) | `gmv_net`, `orders`, `aov`, `target_achievement_pct`, `repeat_customer_rate_pct`, `inventory_turnover`, `top_store_growth` |
| **Store Manager** (1 CH) | `gmv_net`, `orders`, `aov`, `target_achievement_pct`, `conversion_proxy`, `return_rate_pct`, `low_stock_sku_n` |

### 7.2 Định nghĩa công thức KPI

| KPI | Domain | Formula | Source Fields | Validate |
|-----|--------|---------|---------------|----------|
| `gmv_net` | Sales | `SUM(NeedPayAmount) WHERE DeleteAt IS NULL AND CompleteAt in period` | `SaleOrder.NeedPayAmount`, `CompleteAt`, `SiteId`, `DeleteAt` | ✅ |
| `orders` | Sales | `COUNT(DISTINCT Id)` | `SaleOrder.Id`, `CompleteAt`, `DeleteAt`, `SiteId` | ✅ |
| `aov` | Sales | `SUM(NeedPayAmount) / COUNT(DISTINCT Id)` | | ⚠️ Có loại đơn 0đ? |
| `return_rate_pct` | Sales | `return_amount / gross_sales` | `ReturnSaleOrder`, `SaleOrder` | ⚠️ Denominator: gross hay net? |
| `top_store_growth` | Sales | Period-over-period growth by site | `SaleOrder`, `Site` | |
| `new_customers` | Customer | `COUNT(Customer.Id) created in period` | `Customer.Id`, `CreateAt`, `SiteId`, `DeleteAt` | ⚠️ "Created" vs "first order"? |
| `repeat_customer_rate_pct` | Customer | `customers ≥2 orders / active customers` | `SaleOrder.CustomerId` | ⚠️ Lookback window? |
| `conversion_proxy` | Customer | `orders per active session hour` | `SaleOrder`, `PosSession.OpenAt/CloseAt` | ⚠️ Proxy, không phải true conversion |
| `inventory_turnover` | Inventory | `COGS / avg inventory cost` | `StockHistory`, `Product.CostPrice` | |
| `stockout_risk_sku_n` | Inventory | `SKU with low coverage threshold` | `StockItem`, `Product` | ⚠️ Threshold bao nhiêu ngày? |
| `low_stock_sku_n` | Inventory | `COUNT SKU below reorder point` | `StockItem` | ⚠️ Reorder point từ đâu? |
| `gross_margin_pct` | Finance | `(SUM(SubTotal) - SUM(SubTotalCostPrice)) / SUM(SubTotal)` | `SaleOrderItem` | ✅ |
| `net_margin_pct` | Finance | `(gross_profit - opex) / revenue` | `SaleOrderItem` + `operational_cost_fact` | ⚠️ `operational_cost_fact` chưa có! |
| `target_achievement_pct` | Finance | `actual / target` | `monthly_targets` + `daily_sales_finance` | ✅ |
| `campaign_revenue_share_pct` | Marketing | `campaign attributed revenue / total revenue` | `PromotionCampaignSaleOrder`, `SaleOrder` | |

---

## 8. Business Rules & Formulas

### 8.1 Quy tắc lọc dữ liệu

| Rule | Logic | Áp dụng |
|------|-------|---------|
| **Soft delete** | `delete_at IS NULL` | Tất cả bảng, tất cả layer |
| **Đơn hoàn tất** | `complete_at IS NOT NULL` | Khi tính doanh thu/đơn hàng |
| **Đơn hủy** | Bỏ qua khi `cancel_at IS NOT NULL` | Implicit qua complete_at filter |
| **Active product** | `delete_at IS NULL AND state active` | dim_product |
| **Active store** | `delete_at IS NULL AND state = 1` | dim_store |

### 8.2 Công thức tính toán

| Metric | Formula | Đơn vị |
|--------|---------|--------|
| **Revenue (Doanh thu thuần)** | `SUM(need_pay_amount)` | VND |
| **COGS (Giá vốn)** | `SUM(sale_order_item.cost_amount)` | VND |
| **Gross Profit** | `revenue_net - cogs_amount` | VND |
| **GPM %** | `gross_profit / revenue_net × 100` | % |
| **NPM % (MVP)** | `(1 - cogs_ratio - opex_ratio) × 100` | % |
| **AOV** | `revenue_net / orders_n` | VND/đơn |
| **UPT (Units per Transaction)** | `units_sold / orders_n` | SP/đơn |
| **Dead stock %** | `100 × units_>90d / total_active_units` | % |
| **Stock cover days** | `active_units / (units_sold / 30)` | ngày |
| **Sell-through rate** | `100 × units_sold / (on_hand + units_sold)` | % |
| **ABC class** | A: cum_rev ≤70%, B: ≤90%, C: rest | category |
| **GMROI** | `gross_profit / avg_inventory_value` | ratio |
| **Retention rate** | `retained / customers_prev` | % |
| **Churn rate** | `churned / customers_prev` | % |
| **RFM scores** | Quintile (1-5) trên Recency/Frequency/Monetary 12 tháng | score |
| **Target achievement** | `actual_revenue / target_revenue × 100` | % |
| **Conversion proxy** | `orders / active_session_hours` | đơn/giờ |

### 8.3 Channel mapping priority

```
1. Nếu có ecom_source_id → map ecom_source.type:
   1=shopee, 2=lazada, 3=tiki, 4=tiktok_shop
2. Nếu không có ecom_source → check sale_channel.name:
   chứa 'web' → 'web'
3. Default → 'offline'
```

### 8.4 Customer segmentation

| Segment | Rule |
|---------|------|
| New | Đơn đầu tiên của KH = ngày d |
| Returning | Có đơn trong 180 ngày trước d (nhưng không phải new) |
| Inactive | Tất cả còn lại |

### 8.5 RFM Segment Rules

| Segment | R score | F score | M score |
|---------|---------|---------|---------|
| Champions | 4-5 | 4-5 | 4-5 |
| Loyal | 3-5 | 3-5 | 3-5 |
| At Risk | 1-2 | 3-5 | 3-5 |
| Hibernating | 1-2 | 1-2 | 1-2 |
| _(others rule-based)_ | | | |

### 8.6 Inventory ageing buckets

| Bucket | Days since `inbound_at` to EOM |
|--------|-------------------------------|
| `0-30` | 0 ≤ days ≤ 30 |
| `31-60` | 31 ≤ days ≤ 60 |
| `61-90` | 61 ≤ days ≤ 90 |
| `91-180` | 91 ≤ days ≤ 180 |
| `180+` | days > 180 |

---

## 9. Data Contracts

| Contract | Quy ước | Enforce tại |
|----------|---------|-------------|
| **Timezone** | `Asia/Ho_Chi_Minh` — tất cả timestamps convert TZ trước khi cắt ngày | `loader.py:DATE_SOURCE`, `pos_sync.py` |
| **Currency** | VND, đơn vị **đồng nguyên** (không chia 1000) | Bronze giữ DOUBLE; serving cast INT |
| **Date field** `d` | Derived từ timestamp chính của bảng (xem §2.7) | Mọi bảng Bronze + fact Silver |
| **Grain prefix** | `daily_*` = (store_id, d); `monthly_*` = (store_id, year_month) | Naming convention |
| **New customer** | First purchase ever = ngày d (lookback window N/A) | `s_daily_customer_segments.sql` |
| **Returning** | Có order trong 180 ngày trước | Silver SQL |
| **Funnel link** | `measurement_ticket_sale_order_item` bridge → item → order | `s_daily_measurement_funnel.sql` |
| **Inventory unit** | 1 row `stock_item` = 1 physical unit | `s_monthly_inventory*.sql` |
| **GMROI dependency** | Cần `monthly_inventory_sku` trước | File: `s_monthly_z_gmroi_category.sql` |
| **Idempotency** | Tất cả Silver/Gold dùng `ON CONFLICT ... DO UPDATE` (UPSERT) | Mọi SQL script |
| **Execution order** | `s_00_*` (dim) → `s_*` (facts) → `s_*_z_*` (dependent) | Alphabetical filename |

---

## 10. Leader Validation Checklist

### ✅ Tính đúng đắn (Correctness)

| # | Câu hỏi | Status | Ghi chú |
|---|---------|--------|---------|
| 1 | Revenue = `need_pay_amount` (net sau giảm giá, có VAT) — đúng ý nghĩa "doanh thu thuần"? | ❓ | Có nên dùng `need_pay_amount_ignore_vat` thay? |
| 2 | COGS lấy từ `sale_order_item.cost_amount` (line item) — khớp với `sale_order.cost_amount` (header)? | ❓ | Có thể sai lệch nếu header khác tổng items |
| 3 | `new_customers` KPI: dùng `Customer.CreateAt` hay "first order date"? | ❓ | `kpi_contract` dùng CreateAt; segment dùng first order |
| 4 | `net_margin_pct` phụ thuộc `operational_cost_fact` — bảng này chưa tồn tại? | ⚠️ | MVP dùng mock `opex_ratio = 8-12%` |
| 5 | `stockout_risk_sku_n` / `low_stock_sku_n` — threshold cụ thể? | ❓ | Chưa define trong code |
| 6 | Dead stock threshold 90 ngày — có phù hợp với ngành kính mắt HMK? | ❓ | Ngành fashion thường 60-90d |
| 7 | ABC thresholds (70/90) — có phù hợp? | ❓ | Industry-standard nhưng cần confirm |
| 8 | `repeat_customer_rate_pct` lookback window — 12 tháng hay 6 tháng? | ❓ | Chưa explicit trong kpi_contract |

### ✅ Tính đầy đủ (Completeness)

| # | Câu hỏi | Status | Ghi chú |
|---|---------|--------|---------|
| 9 | 21 bảng Bronze đủ cho tất cả KPI dashboard? | ✅ | Đã map đủ |
| 10 | Thiếu `dim_region` — region mapping từ đâu? | ⚠️ | Hiện NULL trong dim_store |
| 11 | CSAT/NPS data source (ZNS) đã có pipeline chưa? | ❓ | Config `sources.yml` có `zns_pg` nhưng chưa thấy Bronze |
| 12 | Payment method breakdown (EDP SQLite) — source từ đâu? | ❓ | `daily_payment_methods` chưa có Gold tương ứng |

### ✅ Tính nhất quán (Consistency)

| # | Câu hỏi | Status | Ghi chú |
|---|---------|--------|---------|
| 13 | SQLite `channel_name` vs Gold `channel_key` — cần align tên? | ⚠️ | Có thể gây confusion |
| 14 | SQLite `daily_customer_segments` flatten vs Silver row-per-segment — sync logic đúng? | ❓ | Cấu trúc khác nhau |
| 15 | `dim_store.store_id` = ROW_NUMBER — có stable không khi thêm store? | ⚠️ | Risk: ID thay đổi nếu ORDER BY thay đổi |
| 16 | EDP bảng `monthly_brand_category_metrics` / `daily_payment_methods` — không có Gold source, lấy data từ đâu? | ❓ | Cần bổ sung hoặc document |

### ✅ Data Quality

| # | Câu hỏi | Status | Ghi chú |
|---|---------|--------|---------|
| 17 | Division-by-zero guards cho `retention_rate`, `gmroi`, `aov`? | ❓ | Cần check SQL có NULLIF |
| 18 | Duplicate handling: `ON CONFLICT DO UPDATE` — có risk overwrite bad data? | ❓ | |
| 19 | NULL propagation: khi join fails (LEFT JOIN), measures = NULL hay 0? | ❓ | |
| 20 | Timezone edge case: đơn hoàn tất lúc 23:59 UTC = ngày nào VN? | ✅ | Convert TZ trước cắt ngày |

---

## Phụ lục: Data Sources

| Source | Connection | Tables Used | Incremental Column |
|--------|-----------|-------------|-------------------|
| POS PostgreSQL (pos_pg) | VPN `10.39.93.19:5432` | 21 bảng (xem Bronze) | `UpdateAt` (hoặc `CreatedAt` cho StockHistory) |
| ZNS PostgreSQL (zns_pg) | _(config)_ | Rating, ZaloMessage | `CreatedAt` / `SentAt` |
| Manual targets | EDP SQLite | `monthly_targets` | Manual input (UI) |
| Holidays | EDP SQLite | `holidays` | Manual/seed |

---

_Document generated: 2026-05-19. Pending leader validation._
