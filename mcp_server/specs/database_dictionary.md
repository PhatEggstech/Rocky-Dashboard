# Từ Điển Dữ Liệu Chi Tiết (POS PostgreSQL & Warehouse Gold Schema)

Tài liệu này mô tả chi tiết tất cả các bảng và cột/trường dữ liệu của 2 cơ sở dữ liệu chính trong hệ thống.

## 1. Cơ Sở Dữ Liệu Warehouse (Gold Schema - Báo Cáo)

Bao gồm các bảng đã được tinh lọc và tổng hợp phục vụ trực tiếp cho Dashboard.

### Bảng `gold.stores`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `id` | INTEGER | PRIMARY KEY |
| `name` | TEXT | NOT NULL |
| `region_id` | INTEGER | NOT NULL |
| `region_name` | TEXT | NOT NULL DEFAULT '' |
| `province_id` | UUID |  |
| `pos_site_id` | UUID | UNIQUE |
| `pos_site_guid` | TEXT |  |
| `is_active` | BOOLEAN | NOT NULL DEFAULT TRUE |
| `staff_count` | INTEGER | NOT NULL DEFAULT 0 |
| `strategic_zone` | TEXT |  |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.daily_sales_finance`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `d` | DATE | NOT NULL |
| `orders_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `revenue_net` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `cogs_amount` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `gross_profit` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `units_sold` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `unique_customers_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `remake_orders_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.daily_store_signals`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `d` | DATE | NOT NULL |
| `orders_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `units_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `churn_rate_pct` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.daily_measurement_funnel`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `d` | DATE | NOT NULL |
| `measurement_tickets_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `completed_orders_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `revenue_net` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.monthly_inventory`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `year_month` | TEXT | NOT NULL |
| `dead_stock_pct` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `stock_cover_days` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.monthly_quality_returns`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `year_month` | TEXT | NOT NULL |
| `return_orders_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `return_amount` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `warranty_cases_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `top_reason` | TEXT | NOT NULL DEFAULT '' |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.monthly_customer_retention`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `year_month` | TEXT | NOT NULL |
| `customers_prev` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `customers_curr` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `retained` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `new_acquired` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `churned` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `retention_rate` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `churn_rate` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.dim_product`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `product_id` | UUID | PRIMARY KEY |
| `code` | TEXT |  |
| `name` | TEXT |  |
| `fullname` | TEXT |  |
| `category_id` | UUID |  |
| `category_name` | TEXT |  |
| `brand_id` | UUID |  |
| `brand_name` | TEXT |  |
| `type` | INTEGER |  |
| `cost_price` | DOUBLE | PRECISION |
| `sale_price` | DOUBLE | PRECISION |
| `is_active` | BOOLEAN |  |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.dim_category`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `category_id` | UUID | PRIMARY KEY |
| `code` | TEXT |  |
| `name` | TEXT |  |
| `parent_id` | UUID |  |
| `level` | INTEGER |  |
| `root_id` | UUID |  |
| `root_name` | TEXT |  |
| `is_active` | BOOLEAN |  |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.dim_brand`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `brand_id` | UUID | PRIMARY KEY |
| `code` | TEXT |  |
| `name` | TEXT |  |
| `is_active` | BOOLEAN |  |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.dim_channel`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `channel_key` | TEXT | PRIMARY KEY |
| `label` | TEXT | NOT NULL |
| `source_kind` | TEXT | NOT NULL |
| `sort_order` | INTEGER | NOT NULL DEFAULT 99 |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.dim_campaign`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `campaign_id` | UUID | PRIMARY KEY |
| `code` | TEXT |  |
| `name` | TEXT |  |
| `is_active` | BOOLEAN |  |
| `start_at` | TIMESTAMPTZ |  |
| `end_at` | TIMESTAMPTZ |  |
| `advance_type` | INTEGER |  |
| `note` | TEXT |  |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.daily_channel_sales`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `channel_key` | TEXT | NOT NULL REFERENCES gold.dim_channel(channel_key) |
| `d` | DATE | NOT NULL |
| `orders_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `revenue_net` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `units_sold` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `cogs_amount` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.daily_campaign_sales`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `campaign_id` | UUID | NOT NULL REFERENCES gold.dim_campaign(campaign_id) |
| `d` | DATE | NOT NULL |
| `orders_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `revenue_net` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `promotion_discount` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `customers_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `new_customers_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.daily_customer_segments`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `d` | DATE | NOT NULL |
| `segment_key` | TEXT | NOT NULL |
| `customers_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `revenue_net` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `orders_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.monthly_inventory_sku`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `year_month` | TEXT | NOT NULL |
| `product_id` | UUID | NOT NULL |
| `on_hand_units` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `on_hand_value` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `units_sold` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `revenue_net` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `cogs_amount` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `sell_through_pct` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.monthly_inventory_ageing`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `year_month` | TEXT | NOT NULL |
| `bucket` | TEXT | NOT NULL |
| `units_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `value_amt` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.monthly_abc_sku`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `year_month` | TEXT | NOT NULL |
| `product_id` | UUID | NOT NULL |
| `revenue_net` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `units_sold` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `cum_revenue_pct` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `abc_class` | TEXT | NOT NULL |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.monthly_gmroi_category`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `year_month` | TEXT | NOT NULL |
| `category_id` | UUID | NOT NULL |
| `revenue_net` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `cogs_amount` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `gross_profit` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `avg_inventory_value` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `gmroi` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.monthly_return_reasons`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `year_month` | TEXT | NOT NULL |
| `reason_key` | TEXT | NOT NULL |
| `count_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `amount` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `cum_pct` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.monthly_cohort_retention`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `cohort_ym` | TEXT | NOT NULL |
| `period_idx` | INTEGER | NOT NULL |
| `cohort_size` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `active_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `retention_pct` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.customer_rfm_snapshot`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `snapshot_date` | DATE | NOT NULL |
| `customer_id` | UUID | NOT NULL |
| `store_id` | INTEGER | REFERENCES gold.stores(id) |
| `recency_days` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `frequency_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `monetary` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `r_score` | INTEGER | NOT NULL DEFAULT 0 |
| `f_score` | INTEGER | NOT NULL DEFAULT 0 |
| `m_score` | INTEGER | NOT NULL DEFAULT 0 |
| `rfm_segment` | TEXT | NOT NULL DEFAULT 'unclassified' |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.monthly_csat_store`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `year_month` | TEXT | NOT NULL |
| `total_ratings_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `avg_score` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `pct_4_5_star` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `status_label` | TEXT | NOT NULL DEFAULT 'Good' |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.monthly_store_leaderboard`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `year_month` | TEXT | NOT NULL |
| `revenue_net` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `revenue_prev` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `revenue_growth_pct` | DOUBLE | PRECISION |
| `orders_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `unique_customers_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `conversion_rate_pct` | DOUBLE | PRECISION |
| `atv` | DOUBLE | PRECISION |
| `upt` | DOUBLE | PRECISION |
| `remake_rate_pct` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `staff_count` | INTEGER | NOT NULL DEFAULT 0 |
| `revenue_per_staff` | DOUBLE | PRECISION |
| `revenue_rank` | INTEGER |  |
| `conv_rank` | INTEGER |  |
| `atv_rank` | INTEGER |  |
| `remake_rank` | INTEGER |  |
| `_updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

### Bảng `gold.regions`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `id` | INTEGER | PRIMARY KEY |
| `name` | TEXT | NOT NULL |

### Bảng `gold.holidays`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `d` | DATE | PRIMARY KEY |
| `label` | TEXT |  |

### Bảng `gold.monthly_targets`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `year_month` | TEXT | NOT NULL |
| `gt_weekday` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `gt_weekend` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `gt_holiday` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |

### Bảng `gold.daily_revenue`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `d` | DATE | NOT NULL |
| `amount` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |

### Bảng `gold.daily_store_signals`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `d` | DATE | NOT NULL |
| `orders_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `units_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `churn_rate_pct` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |

### Bảng `gold.monthly_inventory`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `year_month` | TEXT | NOT NULL |
| `dead_stock_pct` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `stock_cover_days` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |

### Bảng `gold.daily_channel_sales`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `d` | DATE | NOT NULL |
| `channel_key` | TEXT | NOT NULL |
| `revenue_net` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `orders_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `units_sold` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `cogs_amount` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `discount_amount` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |

### Bảng `gold.daily_campaign_sales`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `d` | DATE | NOT NULL |
| `campaign_id` | TEXT | NOT NULL |
| `campaign_name` | TEXT | NOT NULL DEFAULT '' |
| `revenue_net` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `orders_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `discount_amount` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |

### Bảng `gold.daily_measurement_funnel`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `d` | DATE | NOT NULL |
| `measurement_tickets_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `completed_orders_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `revenue_net` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |

### Bảng `gold.daily_customer_segments`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `d` | DATE | NOT NULL |
| `segment_key` | TEXT | NOT NULL |
| `customers_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `revenue_net` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `orders_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |

### Bảng `gold.monthly_customer_retention`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `year_month` | TEXT | NOT NULL |
| `customers_prev` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `customers_curr` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `retained` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `new_acquired` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `churned` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `retention_rate` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `churn_rate` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |

### Bảng `gold.monthly_quality_returns`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `year_month` | TEXT | NOT NULL |
| `return_orders_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `return_amount` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `warranty_cases_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `top_reason` | TEXT | NOT NULL DEFAULT '' |

### Bảng `gold.monthly_inventory_sku`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `year_month` | TEXT | NOT NULL |
| `product_id` | TEXT | NOT NULL |
| `product_name` | TEXT | NOT NULL DEFAULT '' |
| `category_name` | TEXT | NOT NULL DEFAULT '' |
| `brand_name` | TEXT | NOT NULL DEFAULT '' |
| `on_hand_value` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `on_hand_units` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `units_sold` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `revenue_net` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `cogs_amount` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `sell_through_pct` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `age_days` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |

### Bảng `gold.monthly_brand_category_metrics`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `year_month` | TEXT | NOT NULL |
| `category_name` | TEXT | NOT NULL |
| `brand_name` | TEXT | NOT NULL |
| `revenue_net` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `gross_profit` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `inventory_value` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `sold_units` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |

### Bảng `gold.daily_payment_methods`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `d` | DATE | NOT NULL |
| `method_name` | TEXT | NOT NULL |
| `amount` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `count` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |

### Bảng `gold.daily_pos_sessions`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `d` | DATE | NOT NULL |
| `session_id` | TEXT | NOT NULL |
| `staff_id` | TEXT | NOT NULL DEFAULT '' |
| `orders_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `revenue_net` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `hours_open` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |

### Bảng `gold.monthly_inventory_ageing`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `year_month` | TEXT | NOT NULL |
| `product_id` | TEXT | NOT NULL DEFAULT '' |
| `age_bucket` | TEXT | NOT NULL |
| `age_days` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `inventory_value` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `units` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |

### Bảng `gold.monthly_return_reasons`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `year_month` | TEXT | NOT NULL |
| `reason_key` | TEXT | NOT NULL |
| `count_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `return_amount` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `cum_pct` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |

### Bảng `gold.monthly_funnel_steps`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `year_month` | TEXT | NOT NULL |
| `step_name` | TEXT | NOT NULL |
| `step_index` | INTEGER | NOT NULL |
| `value` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |

### Bảng `gold.daily_ratings`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `d` | DATE | NOT NULL |
| `ratings_count` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `avg_score` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `score_1` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `score_2` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `score_3` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `score_4` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `score_5` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `response_rate` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |

### Bảng `gold.monthly_csat`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `store_id` | INTEGER | NOT NULL REFERENCES gold.stores(id) |
| `year_month` | TEXT | NOT NULL |
| `ratings_count` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `csat_score` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `response_rate` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `nps_proxy` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |

### Bảng `gold.monthly_cohort_retention`

| Cột | Kiểu dữ liệu | Thuộc tính / Khóa ngoại |
| --- | --- | --- |
| `cohort_ym` | TEXT | NOT NULL |
| `period_idx` | INTEGER | NOT NULL |
| `cohort_size` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `active_n` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |
| `retention_pct` | DOUBLE | PRECISION NOT NULL DEFAULT 0 |


---

## 2. Cơ Sở Dữ Liệu POS PostgreSQL (OLTP - Tác Nghiệp)

Bao gồm 255 bảng chứa dữ liệu nghiệp vụ gốc.

## Table `Account`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 3 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `AvatarLink` | text | YES |  |  |
| `RoleCode` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `Attachment`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `ObjectType` | integer | NO |  |  |
| `ObjectId` | uuid | NO |  |  |
| `Name` | varchar(1000) | YES |  |  |
| `MimeType` | varchar(100) | NO |  |  |
| `Link` | varchar(1000) | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `Attendance`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | text | YES |  |  |
| `State` | integer | NO |  |  |
| `SubmitAt` | timestamp with time zone | YES |  |  |
| `ApprovedAt` | timestamp with time zone | YES |  |  |
| `ApproverNote` | text | YES |  |  |
| `CheckinAt` | timestamp with time zone | YES |  |  |
| `CheckinImageUrl` | text | YES |  |  |
| `CheckinLat` | double precision | YES |  |  |
| `CheckinLng` | double precision | YES |  |  |
| `CheckinDistance` | double precision | YES |  |  |
| `CheckoutAt` | timestamp with time zone | YES |  |  |
| `CheckoutImageUrl` | text | YES |  |  |
| `CheckoutLat` | double precision | YES |  |  |
| `CheckoutLng` | double precision | YES |  |  |
| `CheckoutDistance` | double precision | YES |  |  |
| `IsMeetOwner` | boolean | YES |  |  |
| `Description` | text | YES |  |  |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |
| `ApproverId` | uuid | YES |  | → `Staff`.`Id` |
| `SiteId` | uuid | NO |  | → `Site`.`Id` |
| `NoCheckinImageReasonId` | uuid | YES |  | → `AttendanceReason`.`Id` |
| `NoCheckoutImageReasonId` | uuid | YES |  | → `AttendanceReason`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `AttendanceAttachmentImage`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `ImageUrl` | text | NO |  |  |
| `AttendanceId` | uuid | NO |  | → `Attendance`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `AttendanceReason`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | text | NO |  |  |
| `Title` | text | NO |  |  |
| `Description` | text | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `AuditLog`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |
| `SiteId` | uuid | NO |  | → `Site`.`Id` |
| `ObjectId` | uuid | YES |  |  |
| `Time` | timestamp with time zone | NO |  |  |
| `ExpireAt` | timestamp with time zone | NO |  |  |
| `ObjectType` | integer | NO |  |  |
| `AuditLogMethodType` | integer | NO |  |  |
| `Content` | text | NO |  |  |
| `SubContent` | text | NO |  |  |
| `IpAddress` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `AuditLogDetail`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `AuditLogId` | uuid | NO |  | → `AuditLog`.`Id` |
| `FiledName` | text | NO |  |  |
| `OldValue` | text | YES |  |  |
| `NewValue` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `Bank`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Name` | varchar(500) | NO |  |  |
| `BrandName` | varchar(200) | NO |  |  |
| `SwiftCode` | varchar(100) | NO |  |  |
| `ShortName` | varchar(200) | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `BankAccount`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Name` | varchar(500) | YES |  |  |
| `AccountNumber` | varchar(500) | NO |  |  |
| `Beneficiary` | varchar(500) | NO |  |  |
| `Branch` | varchar(200) | YES |  |  |
| `BankId` | uuid | NO |  | → `Bank`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `BarcodePrintTemplate`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `PageWidth` | double precision | NO |  |  |
| `PageHeight` | double precision | NO |  |  |
| `TemplateData` | text | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `BonusApplyScopeSite`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PayrollBonusId` | uuid | NO |  | → `PayrollBonus`.`Id` |
| `SiteId` | uuid | NO |  | → `Site`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `Brand`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `Name` | varchar(200) | NO |  |  |
| `KiotVietSyncId` | bigint | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `CashFlow`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `Date` | timestamp with time zone | NO |  |  |
| `EndCash` | bigint | NO |  |  |
| `SiteId` | uuid | NO |  | → `Site`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `Commission`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 6 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `State` | integer | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `ApplyScopeAllSite` | boolean | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `ApplyAt` | timestamp with time zone | YES |  |  |
| `ExpireAt` | timestamp with time zone | YES |  |  |

## Table `CommissionApplyScopeSite`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `CommissionId` | uuid | NO |  | → `Commission`.`Id` |
| `SiteId` | uuid | NO |  | → `Site`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `CommissionItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `State` | integer | NO |  |  |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `CommissionId` | uuid | NO |  | → `Commission`.`Id` |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `CommissionAmount` | bigint | NO | 0 |  |
| `CommissionValue` | double precision | NO | 0.0 |  |
| `CommissionValueType` | integer | NO | 0 |  |
| `ProductAmount` | bigint | NO | 0 |  |
| `ProductQuantity` | integer | NO | 0 |  |
| `SaleOrderItemId` | uuid | NO | '00000000-0000-0000-0000-000000000000'::uuid | → `SaleOrderItem`.`Id` |

## Table `CommissionStatement`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `StartAt` | timestamp with time zone | NO |  |  |
| `EndAt` | timestamp with time zone | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `Note` | text | NO | ''::text |  |
| `StaffCount` | integer | NO | 0 |  |
| `State` | integer | NO | 0 |  |
| `TotalCommissionValue` | bigint | NO | 0 |  |
| `SyncedAt` | timestamp with time zone | YES |  |  |
| `CompletedJobCount` | integer | NO | 0 |  |
| `TotalJobCount` | integer | NO | 0 |  |

## Table `CommissionStatementItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `CommissionStatementId` | uuid | NO |  | → `CommissionStatement`.`Id` |
| `CommissionItemId` | uuid | NO |  | → `CommissionItem`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `StaffId` | uuid | NO | '00000000-0000-0000-0000-000000000000'::uuid | → `Staff`.`Id` |

## Table `CommissionStatementJob`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `CommissionStatementId` | uuid | NO |  | → `CommissionStatement`.`Id` |
| `SaleOrderId` | uuid | NO |  | → `SaleOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `State` | integer | NO | 0 |  |

## Table `Company`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `Coupon`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | NO |  |  |
| `State` | integer | NO |  |  |
| `Percent` | integer | YES |  |  |
| `MaxAmount` | bigint | YES |  |  |
| `PublishAt` | timestamp with time zone | YES |  |  |
| `ExpiryAt` | timestamp with time zone | YES |  |  |
| `UseAt` | timestamp with time zone | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `PaymentOrderId` | uuid | YES |  | → `PaymentOrder`.`Id` |
| `CouponCampaignId` | uuid | NO |  | → `CouponCampaign`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `CouponCampaign`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 4 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `IsActive` | boolean | NO |  |  |
| `Code` | varchar(100) | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `Percent` | integer | YES |  |  |
| `MaxAmount` | bigint | YES |  |  |
| `ApplyAllProductCategory` | boolean | NO |  |  |
| `SaleOrderAmountMin` | bigint | YES |  |  |
| `ApplyTimeStartAt` | timestamp with time zone | YES |  |  |
| `ApplyTimeEndAt` | timestamp with time zone | YES |  |  |
| `NumberOfCoupon` | integer | NO |  |  |
| `IsAnyCouponUsed` | boolean | NO |  |  |
| `Note` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `CouponCampaignProduct`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `CouponCampaignId` | uuid | NO |  | → `CouponCampaign`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `CouponCampaignProductCategory`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `CouponCampaignId` | uuid | NO |  | → `CouponCampaign`.`Id` |
| `ProductCategoryId` | uuid | NO |  | → `ProductCategory`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `CouponCampaignSaleOrder`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `CouponCampaignId` | uuid | NO |  | → `CouponCampaign`.`Id` |
| `SaleOrderId` | uuid | NO |  | → `SaleOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `TotalAmount` | bigint | NO | 0 |  |

## Table `Customer`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 12 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `Type` | integer | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `AvatarLink` | text | YES |  |  |
| `IdNo` | text | YES |  |  |
| `Phone` | varchar(20) | YES |  |  |
| `Email` | varchar(500) | YES |  |  |
| `Birthday` | timestamp with time zone | YES |  |  |
| `Gender` | integer | YES |  |  |
| `Facebook` | varchar(1000) | YES |  |  |
| `TaxCode` | varchar(100) | YES |  |  |
| `Note` | text | YES |  |  |
| `StreetAddress` | varchar(500) | YES |  |  |
| `FullAddress` | varchar(1000) | YES |  |  |
| `WardCode` | integer | YES |  | → `Ward`.`Code` |
| `DistrictCode` | integer | YES |  | → `District`.`Code` |
| `ProvinceCode` | integer | YES |  | → `Province`.`Code` |
| `CustomerGroupId` | uuid | YES |  | → `CustomerGroup`.`Id` |
| `CompanyId` | uuid | YES |  | → `Company`.`Id` |
| `KiotVietSyncId` | bigint | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `TotalSaleAmount` | bigint | NO | 0 |  |
| `MinCustomerGroupId` | uuid | YES |  | → `CustomerGroup`.`Id` |
| `LastTransactionAt` | timestamp with time zone | YES |  |  |
| `CurrentDebtAmount` | bigint | NO | 0 |  |
| `TotalSaleAmountIncludeReturnAmount` | bigint | NO | 0 |  |
| `SiteId` | uuid | YES |  | → `Site`.`Id` |
| `Phone2` | varchar(20) | YES |  |  |
| `SearchVector` | tsvector | YES |  |  |
| `HideFromAdmin` | boolean | NO | false |  |
| `DialCode` | varchar(10) | YES |  |  |
| `DialCode2` | varchar(10) | YES |  |  |
| `StandardizedPhone` | varchar(20) | YES |  |  |
| `StandardizedPhone2` | varchar(20) | YES |  |  |
| `NewProvinceCode` | integer | YES |  | → `NewProvince`.`Code` |
| `NewWardCode` | integer | YES |  | → `NewWard`.`Code` |
| `TikTokShopId` | text | YES |  |  |
| `SelfRenameCount` | integer | NO | 0 |  |
| `LazadaId` | text | YES |  |  |
| `ShopeeId` | text | YES |  |  |
| `ParentId` | uuid | YES |  | → `Customer`.`Id` |

## Table `CustomerGroup`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `Name` | varchar(200) | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `AutoCondition` | text | YES |  |  |
| `DiscountType` | integer | NO | 0 |  |
| `DiscountValue` | double precision | NO | 0 |  |
| `Note` | text | YES |  |  |

## Table `CutTicket`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | text | YES |  |  |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |
| `SaleOrderItemId` | uuid | NO |  | → `SaleOrderItem`.`Id` |
| `Quantity` | integer | NO |  |  |
| `Note` | text | YES |  |  |
| `SaleOrderNote` | text | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `SaleOrderId` | uuid | NO | '00000000-0000-0000-0000-000000000000'::uuid | → `SaleOrder`.`Id` |
| `IssueAt` | timestamp with time zone | NO | '-infinity'::timestamp with time zone |  |
| `SiteId` | uuid | NO | '00000000-0000-0000-0000-000000000000'::uuid | → `Site`.`Id` |

## Table `CutTicketItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `CutTicketId` | uuid | NO |  | → `CutTicket`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `Debt`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `IssueAt` | timestamp with time zone | YES |  |  |
| `RefType` | integer | YES |  |  |
| `RefId` | uuid | YES |  |  |
| `RefCode` | varchar(100) | YES |  |  |
| `TargetType` | integer | YES |  |  |
| `TargetId` | uuid | YES |  |  |
| `TargetCode` | varchar(100) | YES |  |  |
| `Value` | bigint | YES |  |  |
| `Balance` | bigint | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `IsCancel` | boolean | NO | false |  |

## Table `DebtAdjustment`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `TargetType` | integer | NO |  |  |
| `TargetId` | uuid | NO |  |  |
| `Value` | bigint | NO |  |  |
| `Description` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `DeliveryRoute`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `Name` | varchar(200) | NO |  |  |
| `StartAt` | integer | NO |  |  |
| `EndAt` | integer | NO |  |  |
| `CutOffTime` | integer | NO |  |  |
| `ShippingFee` | numeric | YES |  |  |
| `IsFree` | boolean | YES |  |  |
| `ShippingMethodId` | uuid | NO |  | → `ShippingMethod`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `TimeZone` | double precision | YES |  |  |
| `RockySyncCode` | varchar(100) | YES |  |  |

## Table `Department`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `Description` | text | YES |  |  |
| `States` | integer | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `District`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Code`
- **Bảng khác FK vào đây:** 9 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Code` | integer | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `ProvinceCode` | integer | NO |  | → `Province`.`Code` |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `EcomProduct`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `SkuCode` | text | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `EcomProductMapping`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `EcomProductId` | uuid | NO |  | → `EcomProduct`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `Quantity` | integer | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `EcomProductSource`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `EcomProductId` | uuid | NO |  | → `EcomProduct`.`Id` |
| `EcomSourceId` | uuid | NO |  | → `EcomSource`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `EcomSource`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 4 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Type` | integer | YES |  |  |
| `ShopId` | text | NO |  |  |
| `ShopName` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `CredentialData` | text | YES |  |  |
| `ShopCipher` | text | YES |  |  |

## Table `EcomWebhookOrderSyncLog`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `IntegrateSource` | integer | NO |  |  |
| `OrderCode` | varchar(128) | NO |  |  |
| `PosOrderId` | uuid | YES |  |  |
| `PosReturnOrderId` | uuid | YES |  |  |
| `SyncAt` | timestamp with time zone | NO |  |  |
| `RetryAt` | timestamp with time zone | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `EpcRequestLog`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Data` | text | NO |  |  |
| `ObjectType` | integer | NO |  |  |
| `Method` | integer | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `ExportHistory`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Name` | text | YES |  |  |
| `MineType` | varchar(100) | NO |  |  |
| `Link` | varchar(1000) | NO |  |  |
| `Type` | integer | NO |  |  |
| `Error` | text | YES |  |  |
| `Success` | boolean | NO |  |  |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `RefId` | uuid | YES |  |  |
| `RefType` | integer | YES |  |  |
| `WorkflowId` | uuid | YES |  | → `Workflow`.`Id` |
| `StateId` | uuid | YES |  | → `WorkflowState`.`Id` |
| `SiteId` | uuid | YES |  | → `Site`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `Holiday`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `StartDate` | timestamp with time zone | NO |  |  |
| `EndDate` | timestamp with time zone | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `ImportHistory`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Name` | text | YES |  |  |
| `MineType` | varchar(100) | NO |  |  |
| `Link` | varchar(1000) | NO |  |  |
| `Type` | integer | NO |  |  |
| `Error` | text | YES |  |  |
| `Success` | boolean | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `RefId` | uuid | YES |  |  |
| `RefType` | integer | YES |  |  |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `SiteId` | uuid | YES |  | → `Site`.`Id` |
| `StateId` | uuid | YES |  | → `WorkflowState`.`Id` |
| `WorkflowId` | uuid | YES |  | → `Workflow`.`Id` |

## Table `InboundDelivery`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `Note` | text | YES |  |  |
| `Quantity` | integer | NO |  |  |
| `SubQuantity` | integer | NO |  |  |
| `ProductAmount` | bigint | YES |  |  |
| `StaffId` | uuid | YES |  | → `Staff`.`Id` |
| `WarehouseId` | uuid | YES |  | → `Warehouse`.`Id` |
| `PurchaseOrderId` | uuid | YES |  | → `PurchaseOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `ReturnSupplierOrderId` | uuid | YES |  | → `ReturnSupplierOrder`.`Id` |

## Table `InboundDeliveryItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Quantity` | integer | YES |  |  |
| `Price` | double precision | NO |  |  |
| `SubTotal` | bigint | YES |  |  |
| `Note` | text | YES |  |  |
| `InboundDeliveryId` | uuid | NO |  | → `InboundDelivery`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `InboundDeliveryStockItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `InboundDeliveryItemId` | uuid | NO |  | → `InboundDeliveryItem`.`Id` |
| `StockItemId` | uuid | NO |  | → `StockItem`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `LazadaWebhookLog`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `RequestHeader` | text | YES |  |  |
| `RequestContent` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `Ledger`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 3 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Type` | integer | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `AccountNumber` | varchar(100) | YES |  |  |
| `Balance` | bigint | NO |  |  |
| `SiteId` | uuid | YES |  | → `Site`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `Code` | varchar(100) | YES |  |  |

## Table `LedgerCollect`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `Amount` | bigint | NO |  |  |
| `Description` | text | YES |  |  |
| `OutcomeTransactionId` | uuid | NO |  | → `LedgerTransaction`.`Id` |
| `IncomeTransactionId` | uuid | NO |  | → `LedgerTransaction`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `LedgerCollectImage`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `LedgerCollectId` | uuid | NO |  | → `LedgerCollect`.`Id` |
| `ImageLink` | text | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `LedgerPeriod`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `StartBalance` | bigint | NO |  |  |
| `EndBalance` | bigint | YES |  |  |
| `Income` | bigint | NO |  |  |
| `Outcome` | bigint | NO |  |  |
| `LedgerId` | uuid | NO |  | → `Ledger`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `LedgerStaff`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `LedgerId`, `StaffId`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `LedgerId` | uuid | NO |  | → `Ledger`.`Id` |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |

## Table `LedgerTransaction`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 4 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `TransactionType` | integer | NO |  |  |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `Amount` | bigint | NO |  |  |
| `Description` | text | YES |  |  |
| `LedgerId` | uuid | NO |  | → `Ledger`.`Id` |
| `PaymentOrderId` | uuid | YES |  | → `PaymentOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `SiteId` | uuid | YES |  | → `Site`.`Id` |

## Table `LedgerTransfer`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `Amount` | bigint | NO |  |  |
| `Description` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `IncomeTransactionId` | uuid | NO | '00000000-0000-0000-0000-000000000000'::uuid | → `LedgerTransaction`.`Id` |
| `OutcomeTransactionId` | uuid | NO | '00000000-0000-0000-0000-000000000000'::uuid | → `LedgerTransaction`.`Id` |

## Table `LenSpectrumRocky`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `MinSph` | double precision | YES |  |  |
| `MaxSph` | double precision | YES |  |  |
| `StepSph` | double precision | YES |  |  |
| `MinCyl` | double precision | YES |  |  |
| `MaxCyl` | double precision | YES |  |  |
| `StepCyl` | double precision | YES |  |  |
| `MinAdd` | double precision | YES |  |  |
| `MaxAdd` | double precision | YES |  |  |
| `StepAdd` | double precision | YES |  |  |
| `ProductRockyId` | uuid | NO |  | → `ProductRocky`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `MeasurementTicket`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 3 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | text | NO |  |  |
| `CustomerId` | uuid | NO |  | → `Customer`.`Id` |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `Note` | text | YES |  |  |
| `DistancePD` | real | YES |  |  |
| `NearPD` | real | YES |  |  |
| `NearRightSphere` | real | YES |  |  |
| `NearRightCylinder` | real | YES |  |  |
| `NearRightAxis` | real | YES |  |  |
| `NearRightAdd` | real | YES |  |  |
| `NearLeftSphere` | real | YES |  |  |
| `NearLeftCylinder` | real | YES |  |  |
| `NearLeftAxis` | real | YES |  |  |
| `NearLeftAdd` | real | YES |  |  |
| `DistanceRightSphere` | real | YES |  |  |
| `DistanceRightCylinder` | real | YES |  |  |
| `DistanceRightAxis` | real | YES |  |  |
| `DistanceRightAdd` | real | YES |  |  |
| `DistanceLeftSphere` | real | YES |  |  |
| `DistanceLeftCylinder` | real | YES |  |  |
| `DistanceLeftAxis` | real | YES |  |  |
| `DistanceLeftAdd` | real | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `SiteId` | uuid | NO | '00000000-0000-0000-0000-000000000000'::uuid | → `Site`.`Id` |
| `Type` | integer | NO | 0 |  |
| `PrintCount` | integer | NO | 0 |  |

## Table `MeasurementTicketPreOrderItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `MeasurementTicketId` | uuid | NO |  | → `MeasurementTicket`.`Id` |
| `PreOrderItemId` | uuid | NO |  | → `PreOrderItem`.`Id` |
| `Type` | integer | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `MeasurementTicketPrintLog`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Data` | text | YES |  |  |
| `MeasurementTicketId` | uuid | NO |  | → `MeasurementTicket`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `MeasurementTicketSaleOrderItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `MeasurementTicketId` | uuid | NO |  | → `MeasurementTicket`.`Id` |
| `SaleOrderItemId` | uuid | NO |  | → `SaleOrderItem`.`Id` |
| `Type` | integer | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `MerchantSite`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | NO |  |  |
| `Passcode` | varchar(100) | NO |  |  |
| `SiteId` | uuid | NO |  | → `Site`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `NewProvince`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Code`
- **Bảng khác FK vào đây:** 7 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Code` | integer | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `NewWard`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Code`
- **Bảng khác FK vào đây:** 6 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Code` | integer | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `ProvinceCode` | integer | NO |  | → `NewProvince`.`Code` |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `NganLuongPaymentOrder`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `ObjectType` | integer | NO |  |  |
| `ObjectId` | uuid | NO |  |  |
| `TokenCode` | text | YES |  |  |
| `CheckoutUrl` | text | YES |  |  |
| `QrCode` | text | YES |  |  |
| `InputData` | text | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `ExpiredAt` | timestamp with time zone | YES |  |  |
| `State` | integer | YES |  |  |
| `ReponseData` | text | YES |  |  |
| `MerchantSiteCode` | text | YES |  |  |

## Table `NganLuongPaymentOrderHistory`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `NganLuongPaymentOrderId` | uuid | NO |  | → `NganLuongPaymentOrder`.`Id` |
| `Data` | text | NO |  |  |
| `State` | integer | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `NganLuongWebhookLog`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Type` | integer | NO |  |  |
| `Data` | text | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `ObjectStateLog`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `TargetType` | integer | NO |  |  |
| `TargetId` | uuid | NO |  |  |
| `FromStateId` | uuid | YES |  | → `WorkflowState`.`Id` |
| `ToStateId` | uuid | YES |  | → `WorkflowState`.`Id` |
| `ActorId` | uuid | YES |  | → `Account`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `ObjectVersionData`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `ObjectType` | integer | NO |  |  |
| `ObjectId` | uuid | NO |  |  |
| `Data` | text | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `OrderAddressInfo`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `DistrictCode` | integer | NO |  | → `District`.`Code` |
| `ProvinceCode` | integer | NO |  | → `Province`.`Code` |
| `WardCode` | integer | YES |  | → `Ward`.`Code` |
| `StreetAddress` | varchar(500) | NO |  |  |
| `FullAddress` | varchar(1000) | NO |  |  |
| `Lat` | double precision | YES |  |  |
| `Long` | double precision | YES |  |  |
| `ZipCode` | varchar(200) | YES |  |  |
| `ReceiverPhone` | varchar(200) | YES |  |  |
| `SiteId` | uuid | NO |  | → `Site`.`Id` |
| `OrderShippingInfoId` | uuid | NO |  | → `OrderShippingInfo`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `ReceiverName` | varchar(200) | YES |  |  |

## Table `OrderDeliveryRoute`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `DeliveryRouteCode` | varchar(100) | YES |  |  |
| `DeliveryRouteName` | varchar(200) | NO |  |  |
| `StartAt` | integer | NO |  |  |
| `EndAt` | integer | NO |  |  |
| `CutOffTime` | integer | NO |  |  |
| `ShippingFee` | numeric | YES |  |  |
| `IssueAt` | timestamp with time zone | YES |  |  |
| `DeliveryRouteId` | uuid | NO |  | → `DeliveryRoute`.`Id` |
| `OrderShippingInfoId` | uuid | NO |  | → `OrderShippingInfo`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `OrderShippingInfo`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `ShippingFee` | numeric | YES |  |  |
| `IsFree` | boolean | YES |  |  |
| `ExpectedAtFrom` | timestamp with time zone | YES |  |  |
| `ExpectedAtTo` | timestamp with time zone | YES |  |  |
| `SupplierOrderId` | uuid | NO |  | → `SupplierOrder`.`Id` |
| `ShippingMethodId` | uuid | NO |  | → `ShippingMethod`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `OutboundDelivery`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `Quantity` | integer | NO |  |  |
| `SubQuantity` | integer | NO |  |  |
| `ProductAmount` | bigint | YES |  |  |
| `Note` | text | YES |  |  |
| `StaffId` | uuid | YES |  | → `Staff`.`Id` |
| `WarehouseId` | uuid | NO |  | → `Warehouse`.`Id` |
| `SaleOrderId` | uuid | YES |  | → `SaleOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `ReturnSupplierOrderId` | uuid | YES |  | → `ReturnSupplierOrder`.`Id` |

## Table `OutboundDeliveryItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Quantity` | integer | NO |  |  |
| `Price` | double precision | NO |  |  |
| `SubTotal` | bigint | NO |  |  |
| `Note` | text | YES |  |  |
| `OutboundDeliveryId` | uuid | NO |  | → `OutboundDelivery`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `OutboundDeliveryStockItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `OutboundDeliveryItemId` | uuid | NO |  | → `OutboundDeliveryItem`.`Id` |
| `StockItemId` | uuid | NO |  | → `StockItem`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `OvertimeSalary`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `SalaryStructureId` | uuid | NO |  | → `SalaryStructure`.`Id` |
| `SalaryOrdinaryDay` | text | NO |  |  |
| `SalarySaturday` | text | NO |  |  |
| `SalarySunday` | text | NO |  |  |
| `SalaryHoliday` | text | NO |  |  |
| `SalaryFestival` | text | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PackingList`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 3 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `SubmitAt` | timestamp with time zone | YES |  |  |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `Quantity` | integer | NO |  |  |
| `SubQuantity` | integer | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `CancelReason` | text | YES |  |  |
| `Note` | text | YES |  |  |

## Table `PackingListItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PackingListId` | uuid | NO |  | → `PackingList`.`Id` |
| `ProductCode` | text | NO |  |  |
| `ProductName` | text | NO |  |  |
| `Quantity` | integer | NO |  |  |
| `ProductId` | uuid | YES |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `IntegrateSource` | integer | NO | 0 |  |
| `SaleOrderId` | uuid | NO | '00000000-0000-0000-0000-000000000000'::uuid | → `SaleOrder`.`Id` |
| `Note` | text | NO | ''::text |  |
| `Price` | double precision | NO | 0.0 |  |

## Table `PackingListSaleOrder`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PackingListId` | uuid | NO |  | → `PackingList`.`Id` |
| `SaleOrderId` | uuid | NO |  | → `SaleOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PaymentMethod`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 6 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `KiotVietSyncId` | bigint | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PaymentOrder`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 6 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `DocumentType` | integer | NO |  |  |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `TargetType` | integer | NO |  |  |
| `TargetId` | uuid | YES |  |  |
| `ObjectType` | integer | NO |  |  |
| `ObjectId` | uuid | YES |  |  |
| `NeedPayAmount` | bigint | NO |  |  |
| `PaidAmount` | bigint | NO |  |  |
| `Note` | text | YES |  |  |
| `PromotionDiscountAmount` | bigint | YES |  |  |
| `PaymentMethodId` | uuid | YES |  | → `PaymentMethod`.`Id` |
| `PaymentTypeId` | uuid | YES |  | → `PaymentType`.`Id` |
| `SaleOrderId` | uuid | YES |  | → `SaleOrder`.`Id` |
| `ReturnSaleOrderId` | uuid | YES |  | → `ReturnSaleOrder`.`Id` |
| `PurchaseOrderId` | uuid | YES |  | → `PurchaseOrder`.`Id` |
| `StaffId` | uuid | YES |  | → `Staff`.`Id` |
| `CustomerId` | uuid | YES |  | → `Customer`.`Id` |
| `SupplierId` | uuid | YES |  | → `Supplier`.`Id` |
| `PaymentOrderStaffId` | uuid | YES |  | → `Staff`.`Id` |
| `SiteId` | uuid | YES |  | → `Site`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `IsCashFlow` | boolean | NO | false |  |
| `PreOrderId` | uuid | YES |  | → `PreOrder`.`Id` |
| `ActualAmount` | bigint | NO | 0 |  |
| `Priority` | integer | YES |  |  |
| `AdvanceAmount` | bigint | NO | 0 |  |
| `PrintCount` | integer | NO | 0 |  |
| `CancelReason` | text | YES |  |  |
| `NganLuongTokenCode` | text | YES |  |  |
| `MerchantSiteCode` | text | YES |  |  |
| `VerifyAt` | timestamp with time zone | YES |  |  |

## Table `PaymentOrderImage`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PaymentOrderId` | uuid | NO |  | → `PaymentOrder`.`Id` |
| `ImageLink` | text | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PaymentOrderPrintLog`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Data` | text | YES |  |  |
| `PaymentOrderId` | uuid | NO |  | → `PaymentOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PaymentRefOrder`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `NotPaidAnyRef` | boolean | NO |  |  |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `NeedPayAmount` | bigint | NO |  |  |
| `PaidAmount` | bigint | NO |  |  |
| `ActualAmount` | bigint | NO |  |  |
| `AdvanceAmount` | bigint | NO |  |  |
| `SaleOrderId` | uuid | YES |  | → `SaleOrder`.`Id` |
| `ReturnSaleOrderId` | uuid | YES |  | → `ReturnSaleOrder`.`Id` |
| `PurchaseOrderId` | uuid | YES |  | → `PurchaseOrder`.`Id` |
| `PreOrderId` | uuid | YES |  | → `PreOrder`.`Id` |
| `PaymentOrderId` | uuid | NO |  | → `PaymentOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PaymentSheet`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `Name` | varchar(200) | NO |  |  |
| `PeriodType` | integer | NO |  |  |
| `PeriodStart` | timestamp with time zone | NO |  |  |
| `PeriodEnd` | timestamp with time zone | NO |  |  |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `StaffId` | uuid | YES |  | → `Staff`.`Id` |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `SiteId` | uuid | NO |  | → `Site`.`Id` |
| `ApplyAllStaff` | boolean | NO |  |  |
| `StaffCount` | integer | NO |  |  |
| `TotalAmount` | bigint | NO |  |  |
| `NeedPayAmount` | bigint | NO |  |  |
| `PaidAmount` | bigint | NO |  |  |
| `Note` | text | YES |  |  |
| `NextSyncAt` | timestamp with time zone | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PaymentSheetApplyStaff`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |
| `PaymentSheetId` | uuid | NO |  | → `PaymentSheet`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PaymentSheetItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `Name` | varchar(200) | NO |  |  |
| `PaymentSheetId` | uuid | YES |  | → `PaymentSheet`.`Id` |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `Note` | text | YES |  |  |
| `SalaryAmount` | bigint | NO |  |  |
| `CommissionAmount` | bigint | NO |  |  |
| `BonusAmount` | bigint | NO |  |  |
| `PenatyAmount` | bigint | NO |  |  |
| `NeedPayAmount` | bigint | NO |  |  |
| `PaidAmount` | bigint | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PaymentType`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `Name` | varchar(200) | NO |  |  |
| `DocumentType` | integer | NO |  |  |
| `CanUpdate` | boolean | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `Description` | text | YES |  |  |
| `ParentId` | uuid | YES |  | → `PaymentType`.`Id` |
| `ParentLevel` | integer | NO | 0 |  |

## Table `PayrollAllowance`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `Type` | integer | NO |  |  |
| `Value` | bigint | NO |  |  |
| `Method` | integer | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PayrollBonus`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 4 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Type` | integer | NO |  |  |
| `Form` | integer | NO |  |  |
| `ApplyScopeAllSite` | boolean | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PayrollBonusCondition`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PayrollBonusId` | uuid | NO |  | → `PayrollBonus`.`Id` |
| `Amount` | bigint | NO |  |  |
| `Method` | integer | NO |  |  |
| `Value` | bigint | YES |  |  |
| `MinAmount` | bigint | YES |  |  |
| `CommissionId` | uuid | YES |  | → `Commission`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PayrollDeduction`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `Type` | integer | NO |  |  |
| `Condition` | integer | YES |  |  |
| `Minute` | integer | YES |  |  |
| `Value` | bigint | NO |  |  |
| `Method` | integer | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PosProductReportReturnAndSaleOrder`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `ObjectId` | uuid | NO |  |  |
| `ObjectTypes` | integer | NO |  |  |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `ProductId` | uuid | YES |  | → `Product`.`Id` |
| `Quantity` | integer | NO |  |  |
| `Renevue` | bigint | YES |  |  |
| `NetRenevue` | bigint | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `SiteId` | uuid | YES |  |  |

## Table `PosSession`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 4 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `Name` | varchar(200) | NO |  |  |
| `State` | integer | NO |  |  |
| `OpenAt` | timestamp with time zone | YES |  |  |
| `CloseAt` | timestamp with time zone | YES |  |  |
| `OpenCash` | bigint | YES |  |  |
| `CloseCash` | bigint | YES |  |  |
| `OpenNote` | text | YES |  |  |
| `CloseNote` | text | YES |  |  |
| `SiteId` | uuid | NO |  | → `Site`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PosSessionStaff`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PosSessionId` | uuid | NO |  | → `PosSession`.`Id` |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `Position`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `Description` | text | YES |  |  |
| `States` | integer | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PreOrder`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 10 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `ExpectAt` | timestamp with time zone | YES |  |  |
| `SubmitAt` | timestamp with time zone | YES |  |  |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `ProductAmount` | bigint | YES |  |  |
| `DiscountAmount` | bigint | YES |  |  |
| `PaidAmount` | bigint | YES |  |  |
| `Note` | text | YES |  |  |
| `DiscountType` | integer | YES |  |  |
| `DiscountValue` | double precision | YES |  |  |
| `Quantity` | integer | NO |  |  |
| `SubQuantity` | integer | NO |  |  |
| `Change` | bigint | YES |  |  |
| `NeedPayAmount` | bigint | YES |  |  |
| `CustomerPaid` | bigint | YES |  |  |
| `IsUnderpay` | boolean | NO |  |  |
| `SaleChannelId` | uuid | YES |  | → `SaleChannel`.`Id` |
| `CustomerId` | uuid | YES |  | → `Customer`.`Id` |
| `PosSessionId` | uuid | YES |  | → `PosSession`.`Id` |
| `StaffId` | uuid | YES |  | → `Staff`.`Id` |
| `SiteId` | uuid | YES |  | → `Site`.`Id` |
| `ProcessingSiteId` | uuid | YES |  | → `Site`.`Id` |
| `PaymentMethodId` | uuid | YES |  | → `PaymentMethod`.`Id` |
| `NeedVat` | boolean | NO |  |  |
| `VatTaxCode` | text | YES |  |  |
| `VatCompanyName` | text | YES |  |  |
| `VatCompanyAddress` | text | YES |  |  |
| `VatCompanyPhone` | text | YES |  |  |
| `VatCompanyEmail` | text | YES |  |  |
| `HasVat` | boolean | NO |  |  |
| `HasUseVoucher` | boolean | NO |  |  |
| `VatLink` | text | YES |  |  |
| `VatMimeType` | text | YES |  |  |
| `KiotVietSyncId` | bigint | YES |  |  |
| `PrintCount` | integer | NO |  |  |
| `PromotionDiscountType` | integer | YES |  |  |
| `PromotionDiscountValue` | double precision | YES |  |  |
| `PromotionDiscountAmount` | bigint | YES |  |  |
| `CouponPercent` | integer | YES |  |  |
| `CouponDiscountAmount` | bigint | YES |  |  |
| `TotalDiscountAmount` | bigint | YES |  |  |
| `VatTypeId` | uuid | YES |  | → `VatType`.`Id` |
| `NeedPayAmountIgnoreVat` | bigint | YES |  |  |
| `VatAmount` | bigint | YES |  |  |
| `SaleOrderCodes` | text | YES |  |  |
| `SaledQuantity` | integer | NO |  |  |
| `LeftQuantity` | integer | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `NeedPayAmountBeforeRound` | bigint | YES |  |  |
| `RoundAmount` | bigint | YES |  |  |
| `IsRound` | boolean | NO | false |  |
| `RefractionistStaffId` | uuid | YES |  | → `Staff`.`Id` |
| `SupplierOrderId` | uuid | YES |  | → `SupplierOrder`.`Id` |
| `NganLuongTokenCode` | text | YES |  |  |
| `MerchantSiteCode` | text | YES |  |  |
| `CompleteAtEnd` | timestamp with time zone | YES |  |  |
| `ParentOrderId` | uuid | YES |  | → `PreOrder`.`Id` |
| `PreOrderType` | integer | YES |  |  |

## Table `PreOrderCode`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | bigint | NO |  |  |

## Table `PreOrderItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 3 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Quantity` | integer | NO |  |  |
| `OriginalPrice` | double precision | NO |  |  |
| `Price` | double precision | NO |  |  |
| `DiscountPrice` | double precision | YES |  |  |
| `DiscountType` | integer | YES |  |  |
| `DiscountValue` | double precision | YES |  |  |
| `ActualPrice` | double precision | NO |  |  |
| `SubTotal` | bigint | NO |  |  |
| `LeftQuantity` | integer | NO |  |  |
| `SaledQuantity` | integer | NO |  |  |
| `Note` | text | YES |  |  |
| `PreOrderId` | uuid | NO |  | → `PreOrder`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `IsPromotionGift` | boolean | NO |  |  |
| `IsPromotionDiscountPrice` | boolean | NO |  |  |
| `PromotionDiscountType` | integer | YES |  |  |
| `PromotionDiscountValue` | double precision | YES |  |  |
| `PromotionDiscountAmount` | double precision | YES |  |  |
| `TotalDiscountAmount` | double precision | YES |  |  |
| `PromotionCampaignItemId` | uuid | YES |  | → `PromotionCampaignItem`.`Id` |
| `VatTypeId` | uuid | YES |  | → `VatType`.`Id` |
| `AmountIgnoreVat` | double precision | YES |  |  |
| `VatAmount` | bigint | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `SupplierOrderItemId` | uuid | YES |  | → `SupplierOrderItem`.`Id` |
| `CurrentStockQuantity` | integer | YES |  |  |

## Table `PreOrderPrintLog`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Data` | text | YES |  |  |
| `PreOrderId` | uuid | NO |  | → `PreOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PreOrderPromotionCampaignGiftProductItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PreOrderPromotionCampaignItemId` | uuid | NO |  | → `PreOrderPromotionCampaignItem`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PreOrderPromotionCampaignGiftVoucherItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PreOrderPromotionCampaignItemId` | uuid | NO |  | → `PreOrderPromotionCampaignItem`.`Id` |
| `VoucherId` | uuid | NO |  | → `Voucher`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PreOrderPromotionCampaignItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 4 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PromotionCampaignItemId` | uuid | NO |  | → `PromotionCampaignItem`.`Id` |
| `PreOrderId` | uuid | NO |  | → `PreOrder`.`Id` |
| `Name` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PreOrderPromotionCampaignProductDiscountItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PreOrderPromotionCampaignItemId` | uuid | NO |  | → `PreOrderPromotionCampaignItem`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PreOrderPromotionCampaignProductItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PreOrderPromotionCampaignItemId` | uuid | NO |  | → `PreOrderPromotionCampaignItem`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PreOrderStockItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PreOrderItemId` | uuid | NO |  | → `PreOrderItem`.`Id` |
| `StockItemId` | uuid | NO |  | → `StockItem`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `Product`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 44 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `Type` | integer | NO |  |  |
| `State` | integer | NO |  |  |
| `Barcode` | varchar(100) | YES |  |  |
| `Name` | varchar(200) | NO |  |  |
| `Fullname` | varchar(1000) | NO |  |  |
| `ImageUrl` | text | YES |  |  |
| `DescriptionHtml` | text | YES |  |  |
| `CostPrice` | double precision | YES |  |  |
| `LastPurchasePrice` | double precision | YES |  |  |
| `SalePrice` | double precision | YES |  |  |
| `SalePriceIgnoreTax` | double precision | YES |  |  |
| `SalePriceIncludeTax` | double precision | YES |  |  |
| `CanSaleOnPos` | boolean | NO |  |  |
| `StockQuantity` | bigint | YES |  |  |
| `StockLimitMin` | integer | YES |  |  |
| `StockLimitMax` | integer | YES |  |  |
| `Weight` | double precision | YES |  |  |
| `UnitName` | varchar(100) | YES |  |  |
| `UnitConversionValue` | integer | YES |  |  |
| `Note` | text | YES |  |  |
| `MasterUnitId` | uuid | YES |  | → `Product`.`Id` |
| `ProductCategoryId` | uuid | YES |  | → `ProductCategory`.`Id` |
| `BrandId` | uuid | YES |  | → `Brand`.`Id` |
| `StockLocationId` | uuid | YES |  | → `StockLocation`.`Id` |
| `VatTypeId` | uuid | YES |  | → `VatType`.`Id` |
| `ProductSaleApplyId` | uuid | YES |  | → `ProductSaleApply`.`Id` |
| `KiotVietSyncId` | bigint | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `Tag` | text | NO | ''::text |  |
| `VatInvoiceName` | varchar(200) | YES |  |  |
| `CanDisplayOnVatInvoice` | boolean | NO | false |  |
| `VatInvoiceCode` | text | YES |  |  |
| `VatInvoiceName2` | text | YES |  |  |
| `SearchVector` | tsvector | YES |  |  |

## Table `ProductAttribute`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `DisplayName` | varchar(200) | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `ProductAttributeValue`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `AttributeId` | uuid | NO |  | → `ProductAttribute`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `Value` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `ProductCategory`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 9 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `Name` | varchar(200) | NO |  |  |
| `ParentId` | uuid | YES |  | → `ProductCategory`.`Id` |
| `HierarchyLevel` | integer | NO |  |  |
| `KiotVietSyncId` | bigint | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `IsLen` | boolean | YES |  |  |

## Table `ProductCategoryRocky`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `Name` | varchar(200) | NO |  |  |
| `ParentId` | uuid | YES |  | → `ProductCategoryRocky`.`Id` |
| `HierarchyLevel` | integer | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `ProductComboItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `ComboId` | uuid | NO |  | → `Product`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `Quantity` | integer | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `ProductCommission`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `CommissionId` | uuid | NO |  | → `Commission`.`Id` |
| `ProductId` | uuid | YES |  | → `Product`.`Id` |
| `Value` | double precision | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `ValueType` | integer | NO | 0 |  |
| `ItemType` | integer | NO | 0 |  |
| `ProductCategoryId` | uuid | YES |  | → `ProductCategory`.`Id` |

## Table `ProductMedia`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `MimeType` | varchar(100) | NO |  |  |
| `MediaUrl` | text | NO |  |  |
| `Priority` | integer | NO |  |  |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `ProductPosRockyMapping`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `ProductRockyId` | uuid | NO |  | → `ProductRocky`.`Id` |
| `ProductRockyItemId` | uuid | NO |  | → `ProductRockyItem`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `ProductRocky`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 4 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(500) | YES |  |  |
| `Name` | text | NO |  |  |
| `UnitPrice` | numeric | YES |  |  |
| `UnitPriceFixed` | numeric | YES |  |  |
| `UnitPrice1` | numeric | YES |  |  |
| `UnitPrice2` | numeric | YES |  |  |
| `PurchasePrice` | numeric | YES |  |  |
| `CostPrice` | numeric | YES |  |  |
| `ProductCategoryRockyId` | uuid | YES |  | → `ProductCategoryRocky`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `Type` | integer | NO | 0 |  |
| `AmisName` | text | YES | ''::text |  |
| `MenuName` | text | YES | ''::text |  |
| `DisplayName` | text | NO | ''::text |  |
| `HmkProductName` | text | YES |  |  |
| `MaxAdd` | double precision | YES |  |  |
| `MaxCyl` | double precision | YES |  |  |
| `MaxSph` | double precision | YES |  |  |
| `MinAdd` | double precision | YES |  |  |
| `MinCyl` | double precision | YES |  |  |
| `MinSph` | double precision | YES |  |  |
| `StepAdd` | double precision | YES |  |  |
| `StepCyl` | double precision | YES |  |  |
| `StepSph` | double precision | YES |  |  |
| `Weight` | double precision | YES |  |  |

## Table `ProductRockyItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(500) | YES |  |  |
| `Name` | text | NO |  |  |
| `UnitPrice` | numeric | YES |  |  |
| `UnitPriceFixed` | numeric | YES |  |  |
| `UnitPrice1` | numeric | YES |  |  |
| `UnitPrice2` | numeric | YES |  |  |
| `PurchasePrice` | numeric | YES |  |  |
| `CostPrice` | numeric | YES |  |  |
| `Sph` | double precision | YES |  |  |
| `Cyl` | double precision | YES |  |  |
| `Add` | double precision | YES |  |  |
| `ProductRockyId` | uuid | NO |  | → `ProductRocky`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `ProductSaleApply`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `TargetType` | integer | NO |  |  |
| `TargetId` | uuid | NO |  |  |
| `SiteId` | uuid | YES |  | → `Site`.`Id` |
| `SiteGroupId` | uuid | YES |  | → `SiteGroup`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `ProductSite`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `SiteId` | uuid | NO |  | → `Site`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `StockQuantity` | bigint | YES |  |  |
| `CostPrice` | double precision | YES |  |  |
| `LastPurchasePrice` | double precision | YES |  |  |
| `SalePrice` | double precision | YES |  |  |
| `SalePriceIgnoreTax` | double precision | YES |  |  |
| `SalePriceIncludeTax` | double precision | YES |  |  |
| `VatTypeId` | uuid | YES |  | → `VatType`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `State` | integer | NO | 0 |  |
| `LockedStockQuantity` | bigint | YES |  |  |
| `IsAllowOrderRocky` | boolean | YES |  |  |
| `EcomItemId` | text | YES |  |  |
| `EcomModelId` | text | YES |  |  |

## Table `PromotionCampaign`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 8 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `IsActive` | boolean | NO |  |  |
| `Code` | varchar(100) | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `LimitPerCustomer` | boolean | NO |  |  |
| `ApplyTimeStartAt` | timestamp with time zone | YES |  |  |
| `ApplyTimeEndAt` | timestamp with time zone | YES |  |  |
| `ApplyTimeMonth` | bigint | YES |  |  |
| `ApplyTimeDate` | bigint | YES |  |  |
| `ApplyTimeWeekday` | bigint | YES |  |  |
| `ApplyTimeHour` | bigint | YES |  |  |
| `ApplyTimeBirthdayCustomer` | boolean | NO |  |  |
| `ApplyScopeAllSite` | boolean | NO |  |  |
| `ApplyScopeAllStaff` | boolean | NO |  |  |
| `ApplyScopeAllCustomer` | boolean | NO |  |  |
| `Note` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `ApplyTimeBirthmonthCustomer` | boolean | NO | false |  |
| `AdvanceType` | integer | YES |  |  |

## Table `PromotionCampaignApplyScopeCustomer`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PromotionCampaignId` | uuid | NO |  | → `PromotionCampaign`.`Id` |
| `CustomerId` | uuid | NO |  | → `Customer`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PromotionCampaignApplyScopeSite`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PromotionCampaignId` | uuid | NO |  | → `PromotionCampaign`.`Id` |
| `SiteId` | uuid | NO |  | → `Site`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PromotionCampaignApplyScopeStaff`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PromotionCampaignId` | uuid | NO |  | → `PromotionCampaign`.`Id` |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PromotionCampaignCustomerPreOrder`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PromotionCampaignId` | uuid | NO |  | → `PromotionCampaign`.`Id` |
| `CustomerId` | uuid | NO |  | → `Customer`.`Id` |
| `PreOrderId` | uuid | NO |  | → `PreOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PromotionCampaignCustomerSaleOrder`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PromotionCampaignId` | uuid | NO |  | → `PromotionCampaign`.`Id` |
| `CustomerId` | uuid | NO |  | → `Customer`.`Id` |
| `SaleOrderId` | uuid | NO |  | → `SaleOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PromotionCampaignGiftProductCategoryItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PromotionCampaignItemId` | uuid | NO |  | → `PromotionCampaignItem`.`Id` |
| `ProductCategoryId` | uuid | NO |  | → `ProductCategory`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PromotionCampaignGiftProductItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PromotionCampaignItemId` | uuid | NO |  | → `PromotionCampaignItem`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PromotionCampaignItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 11 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `PromotionType` | integer | NO |  |  |
| `PromotionMethod` | integer | NO |  |  |
| `SaleOrderAmountMin` | bigint | YES |  |  |
| `ProductQuantity` | integer | YES |  |  |
| `ProductId` | uuid | YES |  | → `Product`.`Id` |
| `SaleOrderDiscountType` | integer | YES |  |  |
| `SaleOrderDiscountValue` | bigint | YES |  |  |
| `ProductDiscountQuantity` | integer | YES |  |  |
| `ProductDiscountId` | uuid | YES |  | → `Product`.`Id` |
| `ProductDiscountType` | integer | YES |  |  |
| `ProductDiscountValue` | bigint | YES |  |  |
| `GiftProductQuantity` | integer | YES |  |  |
| `GiftProductId` | uuid | YES |  | → `Product`.`Id` |
| `GiftVoucherQuantity` | integer | YES |  |  |
| `GiftVoucherId` | uuid | YES |  | → `VoucherCampaign`.`Id` |
| `PromotionCampaignId` | uuid | NO |  | → `PromotionCampaign`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PromotionCampaignPreOrder`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PromotionCampaignId` | uuid | NO |  | → `PromotionCampaign`.`Id` |
| `PreOrderId` | uuid | NO |  | → `PreOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PromotionCampaignProductCategoryDiscountItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PromotionCampaignItemId` | uuid | NO |  | → `PromotionCampaignItem`.`Id` |
| `ProductCategoryId` | uuid | NO |  | → `ProductCategory`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PromotionCampaignProductCategoryItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PromotionCampaignItemId` | uuid | NO |  | → `PromotionCampaignItem`.`Id` |
| `ProductCategoryId` | uuid | NO |  | → `ProductCategory`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PromotionCampaignProductDiscountItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PromotionCampaignItemId` | uuid | NO |  | → `PromotionCampaignItem`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PromotionCampaignProductItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PromotionCampaignItemId` | uuid | NO |  | → `PromotionCampaignItem`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PromotionCampaignSaleOrder`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PromotionCampaignId` | uuid | NO |  | → `PromotionCampaign`.`Id` |
| `SaleOrderId` | uuid | NO |  | → `SaleOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `PromotionCampaignVoucherCampaign`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PromotionCampaignItemId` | uuid | NO |  | → `PromotionCampaignItem`.`Id` |
| `VoucherCampaignId` | uuid | NO |  | → `VoucherCampaign`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `Province`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Code`
- **Bảng khác FK vào đây:** 9 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Code` | integer | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `NewProvinceCode` | integer | YES |  | → `NewProvince`.`Code` |

## Table `PurchaseOrder`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 4 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `ProductAmount` | bigint | YES |  |  |
| `DiscountAmount` | bigint | YES |  |  |
| `PaidAmount` | bigint | YES |  |  |
| `Note` | text | YES |  |  |
| `DiscountType` | integer | YES |  |  |
| `DiscountValue` | double precision | YES |  |  |
| `Quantity` | integer | NO |  |  |
| `SubQuantity` | integer | NO |  |  |
| `Change` | bigint | YES |  |  |
| `NeedPayAmount` | bigint | YES |  |  |
| `IsUnderpay` | boolean | NO |  |  |
| `SupplierId` | uuid | YES |  | → `Supplier`.`Id` |
| `StaffId` | uuid | YES |  | → `Staff`.`Id` |
| `SiteId` | uuid | YES |  | → `Site`.`Id` |
| `PaymentMethodId` | uuid | YES |  | → `PaymentMethod`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `SupplierOrderId` | uuid | YES |  | → `SupplierOrder`.`Id` |
| `IsRocky` | boolean | YES |  |  |

## Table `PurchaseOrderItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Quantity` | integer | NO |  |  |
| `OriginalPrice` | double precision | NO |  |  |
| `Price` | double precision | NO |  |  |
| `DiscountPrice` | double precision | YES |  |  |
| `DiscountType` | integer | YES |  |  |
| `DiscountValue` | double precision | YES |  |  |
| `ActualPrice` | double precision | NO |  |  |
| `SubTotal` | bigint | NO |  |  |
| `Note` | text | YES |  |  |
| `PurchaseOrderId` | uuid | NO |  | → `PurchaseOrder`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `SupplierOrderItemId` | uuid | YES |  | → `SupplierOrderItem`.`Id` |

## Table `PurchaseOrderStockItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PurchaseOrderItemId` | uuid | NO |  | → `PurchaseOrderItem`.`Id` |
| `StockItemId` | uuid | NO |  | → `StockItem`.`Id` |
| `ProductId` | uuid | YES |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `ReturnAndSaleOrderHistory`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `SaleOrderId` | uuid | YES |  | → `SaleOrder`.`Id` |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `CustomerId` | uuid | YES |  | → `Customer`.`Id` |
| `ReturnSaleOrderId` | uuid | YES |  | → `ReturnSaleOrder`.`Id` |
| `ObjectTypes` | integer | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `NeedPayAmount` | bigint | YES |  |  |
| `SiteId` | uuid | YES |  | → `Site`.`Id` |

## Table `ReturnExchangeRequest`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(200) | YES |  |  |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `StaffId` | uuid | YES |  | → `Staff`.`Id` |
| `SiteId` | uuid | YES |  | → `Site`.`Id` |
| `Note` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `ReturnSaleOrder`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 5 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `SubmitAt` | timestamp with time zone | YES |  |  |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `OriginalProductAmount` | bigint | YES |  |  |
| `ProductAmount` | bigint | YES |  |  |
| `DiscountAmount` | bigint | YES |  |  |
| `ReturnFeeAmount` | bigint | YES |  |  |
| `PaidAmount` | bigint | YES |  |  |
| `Note` | text | YES |  |  |
| `DiscountType` | integer | YES |  |  |
| `DiscountValue` | double precision | YES |  |  |
| `ReturnFeeType` | integer | YES |  |  |
| `ReturnFeeValue` | bigint | YES |  |  |
| `Quantity` | integer | NO |  |  |
| `SubQuantity` | integer | NO |  |  |
| `NeedPayAmount` | bigint | YES |  |  |
| `SaleChannelId` | uuid | YES |  | → `SaleChannel`.`Id` |
| `CustomerId` | uuid | YES |  | → `Customer`.`Id` |
| `PosSessionId` | uuid | YES |  | → `PosSession`.`Id` |
| `StaffId` | uuid | YES |  | → `Staff`.`Id` |
| `SiteId` | uuid | YES |  | → `Site`.`Id` |
| `PaymentMethodId` | uuid | YES |  | → `PaymentMethod`.`Id` |
| `SaleOrderId` | uuid | YES |  | → `SaleOrder`.`Id` |
| `ExchangeSaleOrderId` | uuid | YES |  | → `SaleOrder`.`Id` |
| `StockAdjustmentId` | uuid | YES |  | → `StockAdjustment`.`Id` |
| `KiotVietSyncId` | bigint | YES |  |  |
| `PrintCount` | integer | NO |  |  |
| `VatTypeId` | uuid | YES |  | → `VatType`.`Id` |
| `NeedPayAmountIgnoreVat` | bigint | YES |  |  |
| `VatAmount` | bigint | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `SubTotalCostPrice` | double precision | YES |  |  |
| `NeedPayAmountBeforeRound` | bigint | YES |  |  |
| `RoundAmount` | bigint | YES |  |  |
| `IsRound` | boolean | NO | false |  |
| `CancelStockAdjustmentId` | uuid | YES |  | → `StockAdjustment`.`Id` |
| `RefractionistStaffId` | uuid | YES |  | → `Staff`.`Id` |
| `NganLuongTokenCode` | text | YES |  |  |
| `MerchantSiteCode` | text | YES |  |  |
| `IntegrateId` | varchar(100) | YES |  |  |
| `IntegrateSource` | integer | YES |  |  |
| `EcomSourceId` | uuid | YES |  | → `EcomSource`.`Id` |

## Table `ReturnSaleOrderCode`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | bigint | NO |  |  |

## Table `ReturnSaleOrderItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Quantity` | integer | NO |  |  |
| `OriginalPrice` | double precision | NO |  |  |
| `Price` | double precision | NO |  |  |
| `DiscountPrice` | double precision | YES |  |  |
| `DiscountType` | integer | YES |  |  |
| `DiscountValue` | double precision | YES |  |  |
| `ActualPrice` | double precision | NO |  |  |
| `SubTotal` | bigint | NO |  |  |
| `Note` | text | YES |  |  |
| `ReturnSaleOrderId` | uuid | NO |  | → `ReturnSaleOrder`.`Id` |
| `ProductId` | uuid | YES |  | → `Product`.`Id` |
| `SaleOrderItemId` | uuid | YES |  | → `SaleOrderItem`.`Id` |
| `VatTypeId` | uuid | YES |  | → `VatType`.`Id` |
| `AmountIgnoreVat` | double precision | YES |  |  |
| `VatAmount` | bigint | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `CostPrice` | double precision | YES |  |  |
| `SubTotalCostPrice` | double precision | YES |  |  |
| `ProductCode` | text | YES |  |  |
| `ProductName` | text | YES |  |  |

## Table `ReturnSaleOrderPrintLog`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Data` | text | YES |  |  |
| `ReturnSaleOrderId` | uuid | NO |  | → `ReturnSaleOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `ReturnSaleOrderStockItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `ReturnSaleOrderItemId` | uuid | NO |  | → `ReturnSaleOrderItem`.`Id` |
| `StockItemId` | uuid | NO |  | → `StockItem`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `ReturnSupplierOrder`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 7 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `Note` | text | YES |  |  |
| `TotalAmount` | numeric | YES |  |  |
| `TotalQuantity` | integer | NO |  |  |
| `SubQuantity` | integer | NO |  |  |
| `TotalDebt` | numeric | YES |  |  |
| `SupplierId` | uuid | YES |  | → `Supplier`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `RockySyncId` | varchar(500) | YES |  |  |
| `ShippingAt` | timestamp with time zone | YES |  |  |
| `ShippingSiteId` | uuid | YES |  | → `Site`.`Id` |
| `StateId` | uuid | NO | '00000000-0000-0000-0000-000000000000'::uuid | → `WorkflowState`.`Id` |
| `SubStateId` | uuid | YES |  | → `WorkflowState`.`Id` |
| `SubWorkflowId` | uuid | YES |  | → `Workflow`.`Id` |
| `SubmitAt` | timestamp with time zone | YES | '-infinity'::timestamp with time zone |  |
| `WorkflowId` | uuid | NO | '00000000-0000-0000-0000-000000000000'::uuid | → `Workflow`.`Id` |
| `ShippingStaffId` | uuid | YES |  | → `Staff`.`Id` |
| `SaleManagerConfirmed` | boolean | YES |  |  |
| `SaleManagerConfirmedAt` | timestamp with time zone | YES |  |  |
| `CancelReason` | text | YES |  |  |
| `SupplierCancelAt` | timestamp with time zone | YES |  |  |
| `ReturnReasons` | text | YES |  |  |
| `ReceiveSiteId` | uuid | YES |  | → `Site`.`Id` |
| `SiteId` | uuid | YES |  | → `Site`.`Id` |
| `StaffId` | uuid | YES |  | → `Staff`.`Id` |

## Table `ReturnSupplierOrderItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `ReturnSupplierOrderId` | uuid | NO |  | → `ReturnSupplierOrder`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `Priority` | integer | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `CanceledQuantity` | integer | NO | 0 |  |
| `ConfirmedQuantity` | integer | NO | 0 |  |
| `Price` | numeric | NO | 0.0 |  |
| `Quantity` | integer | NO | 0 |  |
| `RejectedRequestQuantity` | integer | NO | 0 |  |
| `ShippedQuantity` | integer | NO | 0 |  |
| `SupplierOrderItemId` | uuid | NO | '00000000-0000-0000-0000-000000000000'::uuid | → `SupplierOrderItem`.`Id` |
| `Debt` | numeric | YES |  |  |
| `ConfirmedSaleManagerQuantity` | integer | NO | 0 |  |
| `RejectedSaleManagerQuantity` | integer | NO | 0 |  |
| `ConfirmedSaleAdminQuantity` | integer | NO | 0 |  |
| `ConfirmedWarehouseQuantity` | integer | NO | 0 |  |
| `RejectedSaleAdminQuantity` | integer | NO | 0 |  |
| `RejectedWarehouseQuantity` | integer | NO | 0 |  |
| `SentQuantity` | integer | NO | 0 |  |

## Table `RevenueAccount`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `UserName` | text | YES |  |  |
| `OtherCustomerCode` | text | YES |  |  |
| `WarehouseCode` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `RockyCustomer`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `RockyCustomerSyncId` | uuid | NO |  |  |
| `RockyCustomerSyncCode` | text | NO |  |  |
| `Type` | integer | NO |  |  |
| `SiteId` | uuid | NO |  | → `Site`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `RockyProductCategoryPos`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `ProductCategoryId` | uuid | NO |  | → `ProductCategory`.`Id` |
| `ProductRockyId` | uuid | NO |  | → `ProductRocky`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `RockyRequestLog`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Data` | text | NO |  |  |
| `ObjectType` | integer | NO |  |  |
| `Method` | integer | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `RockyWebhookLog`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `RockySyncId` | uuid | NO |  |  |
| `Action` | text | NO |  |  |
| `RequestContent` | text | NO |  |  |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `Status` | text | NO |  |  |
| `ErrorMessage` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `ProcessedAt` | timestamp with time zone | YES |  |  |

## Table `SalarySample`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 5 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SalarySampleCommission`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `SalarySampleId` | uuid | NO |  | → `SalarySample`.`Id` |
| `CommissionId` | uuid | NO |  | → `Commission`.`Id` |
| `SaleMinAmount` | bigint | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SalarySamplePayrollAllowance`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `SalarySampleId` | uuid | NO |  | → `SalarySample`.`Id` |
| `PayrollAllowanceId` | uuid | NO |  | → `PayrollAllowance`.`Id` |
| `Type` | integer | NO |  |  |
| `Value` | bigint | NO |  |  |
| `Method` | integer | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SalarySamplePayrollBonus`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `SalarySampleId` | uuid | NO |  | → `SalarySample`.`Id` |
| `PayrollBonusId` | uuid | NO |  | → `PayrollBonus`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SalarySamplePayrollDeduction`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `SalarySampleId` | uuid | NO |  | → `SalarySample`.`Id` |
| `PayrollDeductionId` | uuid | NO |  | → `PayrollDeduction`.`Id` |
| `Type` | integer | NO |  |  |
| `Condition` | integer | YES |  |  |
| `Minute` | integer | YES |  |  |
| `Value` | bigint | NO |  |  |
| `Method` | integer | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SalaryStructure`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 3 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Type` | integer | NO |  |  |
| `Income` | bigint | YES |  |  |
| `AdvancedSetting` | boolean | YES |  |  |
| `Overtime` | boolean | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SaleChannel`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 3 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `Name` | varchar(200) | NO |  |  |
| `IconUrl` | text | YES |  |  |
| `Description` | varchar(1000) | YES |  |  |
| `KiotVietSyncId` | bigint | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `CanUpdate` | boolean | NO | false |  |

## Table `SaleOrder`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 22 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `SubmitAt` | timestamp with time zone | YES |  |  |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `ProductAmount` | bigint | YES |  |  |
| `DiscountAmount` | bigint | YES |  |  |
| `PaidAmount` | bigint | YES |  |  |
| `Note` | text | YES |  |  |
| `DiscountType` | integer | YES |  |  |
| `DiscountValue` | double precision | YES |  |  |
| `Quantity` | integer | NO |  |  |
| `SubQuantity` | integer | NO |  |  |
| `Change` | bigint | YES |  |  |
| `NeedPayAmount` | bigint | YES |  |  |
| `IsUnderpay` | boolean | NO |  |  |
| `ReturnSaleOrderCodes` | text | YES |  |  |
| `ReturnedQuantity` | integer | NO |  |  |
| `CurrentQuantity` | integer | NO |  |  |
| `CanReturn` | boolean | NO |  |  |
| `SaleChannelId` | uuid | YES |  | → `SaleChannel`.`Id` |
| `CustomerId` | uuid | YES |  | → `Customer`.`Id` |
| `PosSessionId` | uuid | YES |  | → `PosSession`.`Id` |
| `StaffId` | uuid | YES |  | → `Staff`.`Id` |
| `SiteId` | uuid | YES |  | → `Site`.`Id` |
| `PaymentMethodId` | uuid | YES |  | → `PaymentMethod`.`Id` |
| `ExchangeParentId` | uuid | YES |  | → `SaleOrder`.`Id` |
| `NeedVat` | boolean | NO |  |  |
| `VatTaxCode` | text | YES |  |  |
| `VatCompanyName` | text | YES |  |  |
| `VatCompanyAddress` | text | YES |  |  |
| `VatCompanyPhone` | text | YES |  |  |
| `VatCompanyEmail` | text | YES |  |  |
| `HasVat` | boolean | NO |  |  |
| `VatLink` | text | YES |  |  |
| `VatMimeType` | text | YES |  |  |
| `KiotVietSyncId` | bigint | YES |  |  |
| `PrintCount` | integer | NO |  |  |
| `PromotionDiscountType` | integer | YES |  |  |
| `PromotionDiscountValue` | bigint | YES |  |  |
| `PromotionDiscountAmount` | bigint | YES |  |  |
| `CouponPercent` | integer | YES |  |  |
| `CouponDiscountAmount` | bigint | YES |  |  |
| `TotalDiscountAmount` | bigint | YES |  |  |
| `VatTypeId` | uuid | YES |  | → `VatType`.`Id` |
| `NeedPayAmountIgnoreVat` | bigint | YES |  |  |
| `VatAmount` | bigint | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `HasUseVoucher` | boolean | NO | false |  |
| `StockAdjustmentId` | uuid | YES |  | → `StockAdjustment`.`Id` |
| `CustomerPaid` | bigint | YES |  |  |
| `PreOrderId` | uuid | YES |  | → `PreOrder`.`Id` |
| `SubTotalCostPrice` | double precision | YES |  |  |
| `NeedPayAmountBeforeRound` | bigint | YES |  |  |
| `RoundAmount` | bigint | YES |  |  |
| `VatState` | integer | NO | 0 |  |
| `IsRound` | boolean | NO | false |  |
| `RefractionistStaffId` | uuid | YES |  | → `Staff`.`Id` |
| `IntegrateId` | varchar(100) | YES |  |  |
| `IntegrateSource` | integer | YES |  |  |
| `PackingListId` | uuid | YES |  | → `PackingList`.`Id` |
| `NganLuongTokenCode` | text | YES |  |  |
| `HasInvoice` | boolean | NO | false |  |
| `VatInvoiceId` | uuid | YES |  | → `VatInvoice`.`Id` |
| `VatInvoiceState` | integer | NO | 0 |  |
| `MerchantSiteCode` | text | YES |  |  |
| `BuyerName` | text | YES |  |  |
| `IsInstantShipping` | boolean | YES |  |  |
| `ShippingCarrier` | text | YES |  |  |
| `EcomSourceId` | uuid | YES |  | → `EcomSource`.`Id` |

## Table `SaleOrderCode`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | bigint | NO |  |  |

## Table `SaleOrderCommission`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `SaleOrderId` | uuid | NO |  | → `SaleOrder`.`Id` |
| `SaleOrderItemId` | uuid | NO |  | → `SaleOrderItem`.`Id` |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |
| `Amount` | bigint | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SaleOrderCoupon`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `SaleOrderId` | uuid | NO |  | → `SaleOrder`.`Id` |
| `CouponId` | uuid | NO |  | → `Coupon`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SaleOrderEcomItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Quantity` | integer | NO |  |  |
| `Price` | double precision | NO |  |  |
| `DiscountPrice` | double precision | YES |  |  |
| `ActualPrice` | double precision | NO |  |  |
| `SubTotal` | bigint | NO |  |  |
| `Note` | text | YES |  |  |
| `SaleOrderId` | uuid | NO |  | → `SaleOrder`.`Id` |
| `ProductCode` | text | YES |  |  |
| `ProductName` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SaleOrderEyePrescription`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `ImageUrl` | text | YES |  |  |
| `DistanceRightSphere` | real | YES |  |  |
| `DistanceRightCylinder` | real | YES |  |  |
| `DistanceRightAxis` | real | YES |  |  |
| `DistanceRightPrism` | text | YES |  |  |
| `DistanceRightBase` | text | YES |  |  |
| `DistanceRightVA` | text | YES |  |  |
| `DistanceLeftSphere` | real | YES |  |  |
| `DistanceLeftCylinder` | real | YES |  |  |
| `DistanceLeftAxis` | real | YES |  |  |
| `DistanceLeftPrism` | text | YES |  |  |
| `DistanceLeftBase` | text | YES |  |  |
| `DistanceLeftVA` | text | YES |  |  |
| `NearPD` | real | YES |  |  |
| `NearWD` | real | YES |  |  |
| `NearRightAdd` | real | YES |  |  |
| `NearRightVA` | text | YES |  |  |
| `NearLeftAdd` | real | YES |  |  |
| `NearLeftVA` | text | YES |  |  |
| `SingleVisionLense` | boolean | NO |  |  |
| `BifocalLense` | boolean | NO |  |  |
| `TrifocalLense` | boolean | NO |  |  |
| `ProgressiveLense` | boolean | NO |  |  |
| `Note` | text | YES |  |  |
| `SaleOrderId` | uuid | NO |  | → `SaleOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `Name` | varchar(200) | YES |  |  |
| `NearLeftPDNear` | real | YES |  |  |
| `NearLeftSegHeight` | real | YES |  |  |
| `NearRightPDNear` | real | YES |  |  |
| `NearRightSegHeight` | real | YES |  |  |
| `Priority` | integer | NO | 0 |  |
| `DistanceLeftBaseCurve` | text | YES |  |  |
| `DistanceLeftPrism2` | text | YES |  |  |
| `DistanceLeftPrism2Direction` | text | YES |  |  |
| `DistanceLeftPrismAngle` | text | YES |  |  |
| `DistanceLeftPrismDirection` | text | YES |  |  |
| `DistancePD` | real | YES |  |  |
| `DistanceRightBaseCurve` | text | YES |  |  |
| `DistanceRightPrism2` | text | YES |  |  |
| `DistanceRightPrism2Direction` | text | YES |  |  |
| `DistanceRightPrismAngle` | text | YES |  |  |
| `DistanceRightPrismDirection` | text | YES |  |  |
| `DistanceWD` | real | YES |  |  |
| `ImageUrl2` | text | YES |  |  |
| `ImageUrl3` | text | YES |  |  |
| `ImageUrl4` | text | YES |  |  |
| `ImageUrl5` | text | YES |  |  |
| `ImageUrl6` | text | YES |  |  |
| `ImageUrl7` | text | YES |  |  |
| `ImageUrl8` | text | YES |  |  |
| `ImageUrl9` | text | YES |  |  |
| `NearLeftCntreThickness` | text | YES |  |  |
| `NearLeftCustomInset` | text | YES |  |  |
| `NearLeftEdgeThickness` | text | YES |  |  |
| `NearLeftOpticalCenter` | text | YES |  |  |
| `NearRightCntreThickness` | text | YES |  |  |
| `NearRightCustomInset` | text | YES |  |  |
| `NearRightEdgeThickness` | text | YES |  |  |
| `NearRightOpticalCenter` | text | YES |  |  |
| `DistanceLeftPD` | real | YES |  |  |
| `DistanceRightPD` | real | YES |  |  |

## Table `SaleOrderItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 7 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Quantity` | integer | NO |  |  |
| `OriginalPrice` | double precision | NO |  |  |
| `Price` | double precision | NO |  |  |
| `DiscountPrice` | double precision | YES |  |  |
| `DiscountType` | integer | YES |  |  |
| `DiscountValue` | double precision | YES |  |  |
| `ActualPrice` | double precision | NO |  |  |
| `SubTotal` | bigint | NO |  |  |
| `CurrentQuantity` | integer | NO |  |  |
| `ReturnedQuantity` | integer | NO |  |  |
| `Note` | text | YES |  |  |
| `SaleOrderId` | uuid | NO |  | → `SaleOrder`.`Id` |
| `ProductId` | uuid | YES |  | → `Product`.`Id` |
| `IsPromotionGift` | boolean | NO |  |  |
| `IsPromotionDiscountPrice` | boolean | NO |  |  |
| `PromotionDiscountType` | integer | YES |  |  |
| `PromotionDiscountValue` | double precision | YES |  |  |
| `PromotionDiscountAmount` | double precision | YES |  |  |
| `TotalDiscountAmount` | double precision | YES |  |  |
| `PromotionCampaignItemId` | uuid | YES |  | → `PromotionCampaignItem`.`Id` |
| `VatTypeId` | uuid | YES |  | → `VatType`.`Id` |
| `AmountIgnoreVat` | double precision | YES |  |  |
| `VatAmount` | bigint | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `PreOrderItemId` | uuid | YES |  | → `PreOrderItem`.`Id` |
| `CostPrice` | double precision | YES |  |  |
| `SubTotalCostPrice` | double precision | YES |  |  |
| `ProductCode` | text | YES |  |  |
| `ProductName` | text | YES |  |  |
| `CutQuantity` | integer | YES |  |  |
| `SaleOrderEcomItemId` | uuid | YES |  | → `SaleOrderEcomItem`.`Id` |

## Table `SaleOrderItemEyePrescription`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Name` | varchar(200) | YES |  |  |
| `ImageUrl` | text | YES |  |  |
| `ImageUrl2` | text | YES |  |  |
| `ImageUrl3` | text | YES |  |  |
| `ImageUrl4` | text | YES |  |  |
| `ImageUrl5` | text | YES |  |  |
| `ImageUrl6` | text | YES |  |  |
| `ImageUrl7` | text | YES |  |  |
| `ImageUrl8` | text | YES |  |  |
| `ImageUrl9` | text | YES |  |  |
| `DistanceRightSphere` | real | YES |  |  |
| `DistanceRightCylinder` | real | YES |  |  |
| `DistanceRightAxis` | real | YES |  |  |
| `DistanceRightPrism` | text | YES |  |  |
| `DistanceRightPrismDirection` | text | YES |  |  |
| `DistanceRightPrismAngle` | text | YES |  |  |
| `DistanceRightPrism2` | text | YES |  |  |
| `DistanceRightPrism2Direction` | text | YES |  |  |
| `DistanceRightBaseCurve` | text | YES |  |  |
| `DistanceRightBase` | text | YES |  |  |
| `DistanceRightVA` | text | YES |  |  |
| `DistanceLeftSphere` | real | YES |  |  |
| `DistanceLeftCylinder` | real | YES |  |  |
| `DistanceLeftAxis` | real | YES |  |  |
| `DistanceLeftPrism` | text | YES |  |  |
| `DistanceLeftPrismDirection` | text | YES |  |  |
| `DistanceLeftPrismAngle` | text | YES |  |  |
| `DistanceLeftPrism2` | text | YES |  |  |
| `DistanceLeftPrism2Direction` | text | YES |  |  |
| `DistanceLeftBaseCurve` | text | YES |  |  |
| `DistanceLeftBase` | text | YES |  |  |
| `DistanceLeftVA` | text | YES |  |  |
| `DistancePD` | real | YES |  |  |
| `DistanceWD` | real | YES |  |  |
| `NearRightAdd` | real | YES |  |  |
| `NearRightPDNear` | real | YES |  |  |
| `NearRightSegHeight` | real | YES |  |  |
| `NearRightCustomInset` | text | YES |  |  |
| `NearRightOpticalCenter` | text | YES |  |  |
| `NearRightCntreThickness` | text | YES |  |  |
| `NearRightEdgeThickness` | text | YES |  |  |
| `NearRightVA` | text | YES |  |  |
| `NearLeftAdd` | real | YES |  |  |
| `NearLeftPDNear` | real | YES |  |  |
| `NearLeftSegHeight` | real | YES |  |  |
| `NearLeftCustomInset` | text | YES |  |  |
| `NearLeftOpticalCenter` | text | YES |  |  |
| `NearLeftCntreThickness` | text | YES |  |  |
| `NearLeftEdgeThickness` | text | YES |  |  |
| `NearLeftVA` | text | YES |  |  |
| `NearPD` | real | YES |  |  |
| `NearWD` | real | YES |  |  |
| `SingleVisionLense` | boolean | NO |  |  |
| `BifocalLense` | boolean | NO |  |  |
| `TrifocalLense` | boolean | NO |  |  |
| `ProgressiveLense` | boolean | NO |  |  |
| `Note` | text | YES |  |  |
| `SaleOrderItemId` | uuid | NO |  | → `SaleOrderItem`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `DistanceLeftPD` | real | YES |  |  |
| `DistanceRightPD` | real | YES |  |  |

## Table `SaleOrderPrintLog`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Data` | text | YES |  |  |
| `SaleOrderId` | uuid | NO |  | → `SaleOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SaleOrderPromotionCampaignGiftProductItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `SaleOrderPromotionCampaignItemId` | uuid | NO |  | → `SaleOrderPromotionCampaignItem`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SaleOrderPromotionCampaignGiftVoucherItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `SaleOrderPromotionCampaignItemId` | uuid | NO |  | → `SaleOrderPromotionCampaignItem`.`Id` |
| `VoucherId` | uuid | NO |  | → `Voucher`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SaleOrderPromotionCampaignItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 4 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `PromotionCampaignItemId` | uuid | NO |  | → `PromotionCampaignItem`.`Id` |
| `SaleOrderId` | uuid | NO |  | → `SaleOrder`.`Id` |
| `Name` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SaleOrderPromotionCampaignProductDiscountItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `SaleOrderPromotionCampaignItemId` | uuid | NO |  | → `SaleOrderPromotionCampaignItem`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SaleOrderPromotionCampaignProductItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `SaleOrderPromotionCampaignItemId` | uuid | NO |  | → `SaleOrderPromotionCampaignItem`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SaleOrderStockItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `SaleOrderItemId` | uuid | NO |  | → `SaleOrderItem`.`Id` |
| `StockItemId` | uuid | NO |  | → `StockItem`.`Id` |
| `ProductId` | uuid | YES |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `Setting`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Code`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Code` | varchar(1000) | NO |  |  |
| `Value` | text | YES |  |  |
| `Description` | text | YES |  |  |

## Table `ShippingMethod`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 5 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `Name` | varchar(200) | NO |  |  |
| `Type` | integer | NO |  |  |
| `Description` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `RockySyncCode` | varchar(100) | YES |  |  |

## Table `ShopeeWebhookLog`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `RequestHeader` | text | YES |  |  |
| `RequestContent` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `Site`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 53 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `State` | integer | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `Phone` | varchar(20) | YES |  |  |
| `Email` | varchar(500) | YES |  |  |
| `StreetAddress` | varchar(500) | NO |  |  |
| `FullAddress` | varchar(1000) | NO |  |  |
| `WardCode` | integer | YES |  | → `Ward`.`Code` |
| `DistrictCode` | integer | NO |  | → `District`.`Code` |
| `ProvinceCode` | integer | NO |  | → `Province`.`Code` |
| `SiteGroupId` | uuid | YES |  | → `SiteGroup`.`Id` |
| `KiotVietSyncId` | bigint | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `WorkingOnFriday` | boolean | NO | false |  |
| `WorkingOnMonday` | boolean | NO | false |  |
| `WorkingOnSaturday` | boolean | NO | false |  |
| `WorkingOnSunday` | boolean | NO | false |  |
| `WorkingOnThursday` | boolean | NO | false |  |
| `WorkingOnTuesday` | boolean | NO | false |  |
| `WorkingOnWednesday` | boolean | NO | false |  |
| `TaxCode` | text | YES |  |  |
| `NewProvinceCode` | integer | YES |  | → `NewProvince`.`Code` |
| `NewWardCode` | integer | YES |  | → `NewWard`.`Code` |
| `NewFullAddress` | varchar(1000) | YES |  |  |
| `StoreName` | text | YES |  |  |
| `TemplateVatInvoiceId` | uuid | YES |  | → `TemplateVatInvoice`.`Id` |
| `CanRelaseCashVatInvoice` | boolean | NO | false |  |
| `Lat` | double precision | YES |  |  |
| `Long` | double precision | YES |  |  |
| `RevenueAccountId` | uuid | YES |  | → `RevenueAccount`.`Id` |
| `TaxCodeVatInvoiceId` | uuid | YES |  | → `TaxCodeVatInvoice`.`Id` |
| `EcomSourceId` | uuid | YES |  | → `EcomSource`.`Id` |

## Table `SiteBankAccount`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `SiteId` | uuid | NO |  | → `Site`.`Id` |
| `BankAccountId` | uuid | NO |  | → `BankAccount`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SiteCheckSetting`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Lat` | double precision | YES |  |  |
| `Long` | double precision | YES |  |  |
| `StreetAddress` | varchar(500) | NO |  |  |
| `FullAddress` | varchar(1000) | NO |  |  |
| `WardCode` | integer | YES |  | → `Ward`.`Code` |
| `DistrictCode` | integer | NO |  | → `District`.`Code` |
| `ProvinceCode` | integer | NO |  | → `Province`.`Code` |
| `SiteId` | uuid | NO |  | → `Site`.`Id` |
| `Radius` | integer | NO |  |  |
| `QRCode` | text | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `SettingKey` | uuid | NO | '00000000-0000-0000-0000-000000000000'::uuid |  |

## Table `SiteGroup`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 3 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `State` | integer | NO |  |  |
| `ParentId` | uuid | YES |  | → `SiteGroup`.`Id` |
| `HierarchyLevel` | integer | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SiteStaff`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `SiteId` | uuid | NO |  | → `Site`.`Id` |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `Staff`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 46 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `IdNo` | text | YES |  |  |
| `Phone` | varchar(20) | YES |  |  |
| `Gender` | integer | YES |  |  |
| `Birthday` | timestamp with time zone | YES |  |  |
| `Email` | varchar(500) | YES |  |  |
| `StreetAddress` | varchar(500) | YES |  |  |
| `FullAddress` | varchar(1000) | YES |  |  |
| `WardCode` | integer | YES |  | → `Ward`.`Code` |
| `DistrictCode` | integer | YES |  | → `District`.`Code` |
| `ProvinceCode` | integer | YES |  | → `Province`.`Code` |
| `Note` | text | YES |  |  |
| `State` | integer | NO |  |  |
| `AccountId` | uuid | YES |  | → `Account`.`Id` |
| `KiotVietSyncId` | bigint | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `PositionId` | uuid | YES |  | → `Position`.`Id` |
| `DepartmentId` | uuid | YES |  | → `Department`.`Id` |
| `Name` | varchar(200) | NO | ''::character varying |  |
| `SalarySampleId` | uuid | YES |  | → `SalarySample`.`Id` |
| `SalaryStructureId` | uuid | YES |  | → `SalaryStructure`.`Id` |
| `SalarySiteId` | uuid | YES |  | → `Site`.`Id` |
| `NewProvinceCode` | integer | YES |  | → `NewProvince`.`Code` |
| `NewWardCode` | integer | YES |  | → `NewWard`.`Code` |

## Table `StaffBonusApplyScopeSite`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `StaffPayrollBonusId` | uuid | NO |  | → `StaffPayrollBonus`.`Id` |
| `SiteId` | uuid | NO |  | → `Site`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `StaffCheckItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `CheckTime` | timestamp with time zone | NO |  |  |
| `CheckType` | integer | NO |  |  |
| `MethodType` | integer | NO | 0 |  |
| `Note` | text | YES |  |  |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |
| `TimeSheetItemId` | uuid | YES |  | → `TimeSheetItem`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `Lat` | double precision | YES |  |  |
| `Long` | double precision | YES |  |  |
| `StaffCheckRequestId` | uuid | YES |  | → `StaffCheckRequest`.`Id` |
| `SiteId` | uuid | YES |  | → `Site`.`Id` |

## Table `StaffCheckRequest`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `CheckTime` | timestamp with time zone | NO |  |  |
| `CheckType` | integer | NO |  |  |
| `MethodType` | integer | NO |  |  |
| `Note` | text | YES |  |  |
| `Detail` | text | YES |  |  |
| `Reason` | text | YES |  |  |
| `Lat` | double precision | YES |  |  |
| `Long` | double precision | YES |  |  |
| `IsApprove` | boolean | YES |  |  |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |
| `TimeSheetItemId` | uuid | YES |  | → `TimeSheetItem`.`Id` |
| `ReviewerId` | uuid | YES |  | → `Account`.`Id` |
| `SiteId` | uuid | NO |  | → `Site`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `StaffCommission`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `CommissionId` | uuid | NO |  | → `Commission`.`Id` |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |
| `SaleMinAmount` | bigint | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `StaffPayrollAllowance`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |
| `PayrollAllowanceId` | uuid | NO |  | → `PayrollAllowance`.`Id` |
| `Type` | integer | NO |  |  |
| `Value` | bigint | NO |  |  |
| `Method` | integer | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `StaffPayrollBonus`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |
| `PayrollBonusId` | uuid | NO |  | → `PayrollBonus`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `ApplyScopeAllSite` | boolean | YES |  |  |
| `Form` | integer | NO | 0 |  |
| `Type` | integer | NO | 0 |  |

## Table `StaffPayrollBonusCondition`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `StaffPayrollBonusId` | uuid | NO |  | → `StaffPayrollBonus`.`Id` |
| `Amount` | bigint | NO |  |  |
| `Method` | integer | NO |  |  |
| `Value` | bigint | YES |  |  |
| `MinAmount` | bigint | YES |  |  |
| `CommissionId` | uuid | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `StaffPayrollDeduction`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |
| `PayrollDeductionId` | uuid | NO |  | → `PayrollDeduction`.`Id` |
| `Type` | integer | NO |  |  |
| `Condition` | integer | YES |  |  |
| `Minute` | integer | YES |  |  |
| `Value` | bigint | NO |  |  |
| `Method` | integer | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `StaffVerification`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | NO |  |  |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |
| `ExpireAt` | timestamp with time zone | NO |  |  |
| `UseAt` | timestamp with time zone | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `StockAdjustment`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 9 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `Note` | text | YES |  |  |
| `Quantity` | bigint | NO |  |  |
| `SubQuantity` | integer | NO |  |  |
| `SubTotal` | double precision | NO |  |  |
| `StaffId` | uuid | YES |  | → `Staff`.`Id` |
| `WarehouseId` | uuid | NO |  | → `Warehouse`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `StockAdjustmentItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Quantity` | bigint | NO |  |  |
| `Price` | double precision | NO |  |  |
| `SubTotal` | double precision | NO |  |  |
| `Note` | text | YES |  |  |
| `StockAdjustmentId` | uuid | NO |  | → `StockAdjustment`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `StockAdjustmentStockItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `StockAdjustmentItemId` | uuid | NO |  | → `StockAdjustmentItem`.`Id` |
| `StockItemId` | uuid | NO |  | → `StockItem`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `StockDamage`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `Note` | text | YES |  |  |
| `Quantity` | integer | NO |  |  |
| `SubQuantity` | integer | NO |  |  |
| `SubTotal` | double precision | NO |  |  |
| `StaffId` | uuid | YES |  | → `Staff`.`Id` |
| `WarehouseId` | uuid | NO |  | → `Warehouse`.`Id` |
| `StockAdjustmentId` | uuid | YES |  | → `StockAdjustment`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `StockDamageItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Quantity` | integer | NO |  |  |
| `Price` | double precision | NO |  |  |
| `SubTotal` | double precision | NO |  |  |
| `Note` | text | YES |  |  |
| `StockDamageId` | uuid | NO |  | → `StockDamage`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `StockDamageStockItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `StockDamageItemId` | uuid | NO |  | → `StockDamageItem`.`Id` |
| `StockItemId` | uuid | NO |  | → `StockItem`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `StockHistory`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `CostPrice` | double precision | YES |  |  |
| `Price` | double precision | YES |  |  |
| `Quantity` | bigint | YES |  |  |
| `EndStock` | bigint | NO |  |  |
| `RefType` | integer | YES |  |  |
| `RefId` | uuid | YES |  |  |
| `WarehouseId` | uuid | NO |  | → `Warehouse`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `IsCancel` | boolean | NO | false |  |
| `SubRefId` | uuid | YES |  |  |
| `SubRefType` | integer | YES |  |  |
| `IsReturn` | boolean | NO | false |  |

## Table `StockItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 11 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `CostPrice` | bigint | YES |  |  |
| `InboundAt` | timestamp with time zone | YES |  |  |
| `OutboundAt` | timestamp with time zone | YES |  |  |
| `DamageAt` | timestamp with time zone | YES |  |  |
| `WarehouseId` | uuid | YES |  | → `Warehouse`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `StockItemHistory`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `CostPrice` | double precision | YES |  |  |
| `Price` | double precision | YES |  |  |
| `RefType` | integer | YES |  |  |
| `RefId` | uuid | YES |  |  |
| `WarehouseId` | uuid | YES |  | → `Warehouse`.`Id` |
| `StockItemId` | uuid | NO |  | → `StockItem`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `IsCancel` | boolean | NO | false |  |
| `SubRefId` | uuid | YES |  |  |
| `SubRefType` | integer | YES |  |  |

## Table `StockLocation`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `Name` | varchar(200) | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `StockTake`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `Note` | text | YES |  |  |
| `StaffId` | uuid | YES |  | → `Staff`.`Id` |
| `WarehouseId` | uuid | NO |  | → `Warehouse`.`Id` |
| `StockAdjustmentId` | uuid | YES |  | → `StockAdjustment`.`Id` |
| `SubQuantity` | integer | NO |  |  |
| `SystemQuantity` | bigint | NO |  |  |
| `ActualQuantity` | bigint | YES |  |  |
| `SystemPrice` | double precision | NO |  |  |
| `ActualPrice` | double precision | YES |  |  |
| `DeviationQuantity` | bigint | YES |  |  |
| `DeviationPrice` | double precision | YES |  |  |
| `DeviationIncreaseQuantity` | bigint | YES |  |  |
| `DeviationIncreasePrice` | double precision | YES |  |  |
| `DeviationDecreaseQuantity` | bigint | YES |  |  |
| `DeviationDecreasePrice` | double precision | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `StockTakeItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `SystemQuantity` | bigint | NO |  |  |
| `ActualQuantity` | bigint | YES |  |  |
| `DeviationQuantity` | bigint | YES |  |  |
| `DeviationPrice` | double precision | YES |  |  |
| `ResultType` | integer | NO |  |  |
| `DeviationType` | integer | YES |  |  |
| `Price` | double precision | NO |  |  |
| `Note` | text | YES |  |  |
| `StockTakeId` | uuid | NO |  | → `StockTake`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `StockTakeStockItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `StockTakeItemId` | uuid | NO |  | → `StockTakeItem`.`Id` |
| `StockItemId` | uuid | NO |  | → `StockItem`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `StockTransferOrder`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `StaffId` | uuid | YES |  | → `Staff`.`Id` |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `SourceCompleteAt` | timestamp with time zone | YES |  |  |
| `DestinationCompleteAt` | timestamp with time zone | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `FromWarehouseId` | uuid | NO |  | → `Warehouse`.`Id` |
| `ToWarehouseId` | uuid | NO |  | → `Warehouse`.`Id` |
| `InboundDeliveryId` | uuid | YES |  | → `InboundDelivery`.`Id` |
| `OutboundDeliveryId` | uuid | YES |  | → `OutboundDelivery`.`Id` |
| `SourceNote` | text | YES |  |  |
| `DestinationNote` | text | YES |  |  |
| `Quantity` | integer | NO |  |  |
| `SubQuantity` | integer | NO |  |  |
| `SubTotal` | double precision | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `IsNotMatch` | boolean | YES | false |  |
| `FromStockAdjustmentId` | uuid | YES |  | → `StockAdjustment`.`Id` |
| `ToStockAdjustmentId` | uuid | YES |  | → `StockAdjustment`.`Id` |
| `PrintCount` | integer | NO | 0 |  |
| `ReturnStockAdjustmentId` | uuid | YES |  | → `StockAdjustment`.`Id` |
| `SupplierOrderId` | uuid | YES |  | → `SupplierOrder`.`Id` |
| `ReturnSupplierOrderId` | uuid | YES |  | → `ReturnSupplierOrder`.`Id` |

## Table `StockTransferOrderItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Quantity` | integer | NO |  |  |
| `Price` | double precision | NO |  |  |
| `SubTotal` | double precision | NO |  |  |
| `Note` | text | YES |  |  |
| `StockTransferOrderId` | uuid | NO |  | → `StockTransferOrder`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `SupplierOrderItemId` | uuid | YES |  | → `SupplierOrderItem`.`Id` |
| `ReturnSupplierOrderItemId` | uuid | YES |  | → `ReturnSupplierOrderItem`.`Id` |

## Table `StockTransferOrderPrintLog`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Data` | text | YES |  |  |
| `StockTransferOrderId` | uuid | NO |  | → `StockTransferOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `StockTransferOrderStockItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `StockTransferOrderItemId` | uuid | NO |  | → `StockTransferOrderItem`.`Id` |
| `StockItemId` | uuid | NO |  | → `StockItem`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `Supplier`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 7 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `State` | integer | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `CompanyName` | varchar(200) | YES |  |  |
| `TaxCode` | varchar(100) | YES |  |  |
| `Phone` | varchar(20) | YES |  |  |
| `Email` | varchar(500) | YES |  |  |
| `WardCode` | integer | YES |  | → `Ward`.`Code` |
| `DistrictCode` | integer | YES |  | → `District`.`Code` |
| `ProvinceCode` | integer | YES |  | → `Province`.`Code` |
| `SupplierGroupId` | uuid | YES |  | → `SupplierGroup`.`Id` |
| `StreetAddress` | varchar(500) | YES |  |  |
| `FullAddress` | varchar(1000) | YES |  |  |
| `Note` | text | YES |  |  |
| `KiotVietSyncId` | bigint | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `NewProvinceCode` | integer | YES |  | → `NewProvince`.`Code` |
| `NewWardCode` | integer | YES |  | → `NewWard`.`Code` |

## Table `SupplierDebt`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `SupplierId` | uuid | NO |  | → `Supplier`.`Id` |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `SupplierOrderId` | uuid | YES |  | → `SupplierOrder`.`Id` |
| `ReturnSupplierOrderId` | uuid | YES |  | → `ReturnSupplierOrder`.`Id` |
| `Note` | text | YES |  |  |
| `Debt` | numeric | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `SiteId` | uuid | NO | '00000000-0000-0000-0000-000000000000'::uuid | → `Site`.`Id` |

## Table `SupplierGroup`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `Name` | varchar(200) | NO |  |  |
| `State` | integer | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SupplierOrder`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 11 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `IssueAt` | timestamp with time zone | YES |  |  |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `TotalAmount` | numeric | YES |  |  |
| `SubQuantity` | integer | YES |  |  |
| `Note` | text | YES |  |  |
| `RockySyncId` | uuid | YES |  |  |
| `ShippingMethodId` | uuid | NO |  | → `ShippingMethod`.`Id` |
| `SupplierId` | uuid | YES |  | → `Supplier`.`Id` |
| `SiteId` | uuid | YES |  | → `Site`.`Id` |
| `StaffId` | uuid | YES |  | → `Staff`.`Id` |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `ParentId` | uuid | YES |  | → `SupplierOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `ProcessingSiteId` | uuid | YES |  | → `Site`.`Id` |
| `ConfirmAt` | timestamp with time zone | YES |  |  |
| `PendingAt` | timestamp with time zone | YES |  |  |
| `TotalQuantity` | integer | YES |  |  |
| `BeneficiarySiteId` | uuid | YES |  | → `Site`.`Id` |
| `DeliveryStateId` | uuid | YES |  | → `WorkflowState`.`Id` |
| `DeliveryWorkflowId` | uuid | YES |  | → `Workflow`.`Id` |
| `TotalDebt` | numeric | YES |  |  |
| `SupplierCancelAt` | timestamp with time zone | YES |  |  |
| `Type` | integer | YES | 0 |  |
| `ResetReason` | text | YES |  |  |

## Table `SupplierOrderItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 5 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `Priority` | integer | NO |  |  |
| `Quantity` | integer | NO |  |  |
| `Price` | numeric | NO |  |  |
| `Note` | text | YES |  |  |
| `SubTotal` | numeric | NO |  |  |
| `SupplierOrderId` | uuid | NO |  | → `SupplierOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `ReceivedQuantity` | integer | NO | 0 |  |
| `ReturnedQuantity` | integer | NO | 0 |  |
| `ShippedQuantity` | integer | NO | 0 |  |
| `CanceledQuantity` | integer | NO | 0 |  |
| `ConfirmedQuantity` | integer | NO | 0 |  |
| `Debt` | numeric | YES |  |  |
| `WarrantyQuantity` | integer | NO | 0 |  |
| `ConfirmedRequestQuantity` | integer | NO | 0 |  |
| `RejectedRequestQuantity` | integer | NO | 0 |  |

## Table `SupplierOrderReturnExchange`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `SubmitAt` | timestamp with time zone | YES |  |  |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `Note` | text | YES |  |  |
| `RockySyncId` | varchar(500) | YES |  |  |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `SupplierId` | uuid | YES |  | → `Supplier`.`Id` |
| `CancelSiteId` | uuid | YES |  | → `Site`.`Id` |
| `SupplierOrderId` | uuid | YES |  | → `SupplierOrder`.`Id` |
| `ReturnSupplierOrderId` | uuid | YES |  | → `ReturnSupplierOrder`.`Id` |
| `ReturnExchangeRequestId` | uuid | YES |  | → `ReturnExchangeRequest`.`Id` |
| `ExchangeSupplierOrderId` | uuid | YES |  | → `SupplierOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `SupplierCancelAt` | timestamp with time zone | YES |  |  |
| `ViewSiteId` | uuid | YES |  | → `Site`.`Id` |
| `Type` | integer | YES | 0 |  |
| `DeviceCancelAt` | timestamp with time zone | YES |  |  |
| `DeviceSubmitAt` | timestamp with time zone | YES |  |  |
| `CancelReason` | text | YES |  |  |

## Table `SupplierWarranty`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `SupplierRejectAt` | timestamp with time zone | YES |  |  |
| `SupplierConfirmAt` | timestamp with time zone | YES |  |  |
| `WarrantyReason` | text | YES |  |  |
| `WarrantyDescription` | text | YES |  |  |
| `TotalQuantity` | double precision | NO |  |  |
| `SubQuantity` | integer | NO |  |  |
| `TotalAmount` | double precision | NO |  |  |
| `RockySyncId` | text | YES |  |  |
| `Note` | text | YES |  |  |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `StateId` | uuid | NO |  | → `WorkflowState`.`Id` |
| `SupplierId` | uuid | YES |  | → `Supplier`.`Id` |
| `SiteId` | uuid | YES |  | → `Site`.`Id` |
| `StaffId` | uuid | YES |  | → `Staff`.`Id` |
| `OriginalSupplierOrderId` | uuid | YES |  | → `SupplierOrder`.`Id` |
| `SupplierOrderId` | uuid | YES |  | → `SupplierOrder`.`Id` |
| `ReturnSupplierOrderId` | uuid | YES |  | → `ReturnSupplierOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `ShippingMethodId` | uuid | NO | '00000000-0000-0000-0000-000000000000'::uuid | → `ShippingMethod`.`Id` |
| `BeneficiarySiteId` | uuid | YES |  | → `Site`.`Id` |
| `SupplierRejectReason` | text | YES |  |  |
| `CancelReason` | text | YES |  |  |

## Table `SupplierWarrantyAddressInfo`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `DistrictCode` | integer | NO |  | → `District`.`Code` |
| `ProvinceCode` | integer | NO |  | → `Province`.`Code` |
| `WardCode` | integer | YES |  | → `Ward`.`Code` |
| `StreetAddress` | varchar(500) | NO |  |  |
| `FullAddress` | varchar(1000) | NO |  |  |
| `Lat` | double precision | YES |  |  |
| `Long` | double precision | YES |  |  |
| `ZipCode` | varchar(200) | YES |  |  |
| `ReceiverPhone` | varchar(200) | YES |  |  |
| `ReceiverName` | varchar(200) | YES |  |  |
| `SiteId` | uuid | NO |  | → `Site`.`Id` |
| `SupplierWarrantyShippingInfoId` | uuid | NO |  | → `SupplierWarrantyShippingInfo`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SupplierWarrantyDeliveryRoute`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `DeliveryRouteCode` | varchar(100) | YES |  |  |
| `DeliveryRouteName` | varchar(200) | NO |  |  |
| `StartAt` | integer | NO |  |  |
| `EndAt` | integer | NO |  |  |
| `CutOffTime` | integer | NO |  |  |
| `ShippingFee` | numeric | YES |  |  |
| `IssueAt` | timestamp with time zone | YES |  |  |
| `DeliveryRouteId` | uuid | NO |  | → `DeliveryRoute`.`Id` |
| `SupplierWarrantyShippingInfoId` | uuid | NO |  | → `SupplierWarrantyShippingInfo`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SupplierWarrantyItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `SupplierWarrantyId` | uuid | NO |  | → `SupplierWarranty`.`Id` |
| `SupplierOrderItemId` | uuid | NO |  | → `SupplierOrderItem`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `Quantity` | integer | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Note` | text | YES |  |  |
| `Price` | numeric | NO |  |  |
| `SubTotal` | numeric | NO |  |  |
| `RejectedQuantity` | integer | NO |  |  |
| `ConfirmedQuantity` | integer | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `SupplierWarrantyShippingInfo`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `ShippingFee` | numeric | YES |  |  |
| `IsFree` | boolean | YES |  |  |
| `ExpectedAtFrom` | timestamp with time zone | YES |  |  |
| `ExpectedAtTo` | timestamp with time zone | YES |  |  |
| `SupplierWarrantyId` | uuid | NO |  | → `SupplierWarranty`.`Id` |
| `ShippingMethodId` | uuid | NO |  | → `ShippingMethod`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `TaxCodeVatInvoice`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `TaxCode` | text | NO |  |  |
| `LeftInvoice` | bigint | NO |  |  |
| `IusseAt` | timestamp with time zone | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `PublishedInvoice` | bigint | NO | 0 |  |
| `AccountantEmail` | text | YES |  |  |
| `AlertInvoice` | bigint | NO | 1500 |  |
| `IsSendEmail` | boolean | YES | false |  |
| `BankAccountId` | uuid | YES |  | → `BankAccount`.`Id` |
| `CompanyAddress` | text | YES |  |  |
| `CompanyLegalName` | text | YES |  |  |
| `PassCode` | text | YES |  |  |
| `UserName` | text | YES |  |  |
| `StoreName` | text | YES |  |  |
| `ViettelCookie` | text | YES |  |  |

## Table `TemplateVatInvoice`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | text | NO |  |  |
| `Serial` | text | NO |  |  |
| `Type` | integer | NO | 0 |  |
| `TaxCodeVatInvoiceId` | uuid | YES |  | → `TaxCodeVatInvoice`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `AlertInvoice` | bigint | NO | 0 |  |
| `IsSendEmail` | boolean | NO | false |  |
| `LeftInvoice` | bigint | YES |  |  |
| `PublishedInvoice` | bigint | YES |  |  |
| `SymbolNumber` | text | NO | ''::text |  |

## Table `TikTokShopWebhookLog`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `RequestHeader` | text | YES |  |  |
| `RequestContent` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `TimeSheetBonus`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `Amount` | bigint | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `TimeSheetItem`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 4 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `DateTime` | timestamp with time zone | NO |  |  |
| `CheckInTime` | timestamp with time zone | YES |  |  |
| `CheckOutTime` | timestamp with time zone | YES |  |  |
| `WorkingTimeStart` | integer | NO |  |  |
| `WorkingTimeEnd` | integer | NO |  |  |
| `CheckTimeStart` | integer | NO |  |  |
| `CheckTimeEnd` | integer | NO |  |  |
| `Note` | text | YES |  |  |
| `OffType` | integer | YES |  |  |
| `ReplaceStaffId` | uuid | YES |  | → `Staff`.`Id` |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `OvertimeType` | integer | YES |  |  |
| `MainStaffId` | uuid | NO |  | → `Staff`.`Id` |
| `WorkingShiftId` | uuid | NO |  | → `WorkingShift`.`Id` |
| `TimeSheetSettingId` | uuid | YES |  | → `TimeSheetSetting`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `CheckInMethodType` | integer | YES |  |  |
| `CheckOutMethodType` | integer | YES |  |  |
| `CheckInSiteId` | uuid | YES |  | → `Site`.`Id` |
| `CheckOutSiteId` | uuid | YES |  | → `Site`.`Id` |

## Table `TimeSheetItemBonus`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Quantity` | integer | NO |  |  |
| `Amount` | bigint | NO |  |  |
| `TimeSheetItemId` | uuid | NO |  | → `TimeSheetItem`.`Id` |
| `TimeSheetBonusId` | uuid | NO |  | → `TimeSheetBonus`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `TimeSheetItemPenalty`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Quantity` | integer | NO |  |  |
| `Amount` | bigint | NO |  |  |
| `TimeSheetItemId` | uuid | NO |  | → `TimeSheetItem`.`Id` |
| `TimeSheetPenaltyId` | uuid | NO |  | → `TimeSheetPenalty`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `TimeSheetPenalty`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `Amount` | bigint | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `TimeSheetSetting`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 1 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `RepeatPerWeek` | boolean | NO |  |  |
| `RepeatUntilAt` | timestamp with time zone | YES |  |  |
| `RepeatOverHoliday` | boolean | NO |  |  |
| `RepeatOnMonday` | boolean | NO |  |  |
| `RepeatOnTuesday` | boolean | NO |  |  |
| `RepeatOnWednesday` | boolean | NO |  |  |
| `RepeatOnThursday` | boolean | NO |  |  |
| `RepeatOnFriday` | boolean | NO |  |  |
| `RepeatOnSaturday` | boolean | NO |  |  |
| `RepeatOnSunday` | boolean | NO |  |  |
| `NextSyncAt` | timestamp with time zone | YES |  |  |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |
| `WorkingShiftId` | uuid | NO |  | → `WorkingShift`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `EndAt` | timestamp with time zone | YES |  |  |
| `StartAt` | timestamp with time zone | NO | '-infinity'::timestamp with time zone |  |

## Table `UnitMeasurement`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Type` | integer | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `Factor` | double precision | NO |  |  |
| `Rounding` | double precision | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `VatInvoice`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 3 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `SupplierTaxCode` | text | YES |  |  |
| `InvoiceNo` | text | YES |  |  |
| `TransactionID` | text | YES |  |  |
| `ReservationCode` | text | YES |  |  |
| `CodeOfTax` | text | YES |  |  |
| `ObjectId` | uuid | NO |  |  |
| `ObjectType` | integer | NO |  |  |
| `BuyerTaxCode` | text | YES |  |  |
| `BuyerName` | text | YES |  |  |
| `BuyerLegalName` | text | YES |  |  |
| `BuyerAddressLine` | text | YES |  |  |
| `BuyerBankName` | text | YES |  |  |
| `BuyerEmail` | text | YES |  |  |
| `BuyerBankAccount` | text | YES |  |  |
| `IssueAt` | timestamp with time zone | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `SiteId` | uuid | YES |  |  |
| `State` | integer | YES |  |  |
| `Note` | text | YES |  |  |
| `NumberNo` | text | YES |  |  |
| `CompleteAt` | timestamp with time zone | YES |  |  |
| `CurrencyType` | text | YES |  |  |
| `InvoiceCode` | text | YES |  |  |
| `Invoicetype` | integer | YES |  |  |
| `LooKUpCode` | text | YES |  |  |
| `ResultMessage` | text | YES |  |  |
| `Total` | bigint | YES |  |  |
| `BuyerPhoneNumber` | text | YES |  |  |
| `SecretCode` | text | YES |  |  |
| `SymbolNumber` | text | YES |  |  |
| `OriginalInvoiceNo` | text | YES |  |  |
| `Serial` | text | YES |  |  |
| `TemplateCode` | text | YES |  |  |
| `DataExportExcel` | text | YES |  |  |
| `DocumentCode` | text | YES |  |  |

## Table `VatInvoiceTransactionLog`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `OriginalVatInvoiceId` | uuid | NO |  | → `VatInvoice`.`Id` |
| `RelatedVatInvoiceId` | uuid | YES |  | → `VatInvoice`.`Id` |
| `SupplierTaxCode` | text | YES |  |  |
| `RequestData` | text | YES |  |  |
| `ReponseData` | text | YES |  |  |
| `CallFunctionName` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `ErrorMessage` | text | YES |  |  |

## Table `VatType`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 8 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Priority` | integer | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `Name` | varchar(200) | NO |  |  |
| `Value` | integer | NO |  |  |
| `PercentValue` | varchar(200) | NO |  |  |
| `IsDefault` | boolean | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `Voucher`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 3 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | NO |  |  |
| `State` | integer | NO |  |  |
| `Amount` | bigint | YES |  |  |
| `PublishAt` | timestamp with time zone | YES |  |  |
| `ExpiryAt` | timestamp with time zone | YES |  |  |
| `UseAt` | timestamp with time zone | YES |  |  |
| `CancelAt` | timestamp with time zone | YES |  |  |
| `Note` | text | YES |  |  |
| `PublishType` | integer | YES |  |  |
| `PaymentMethodId` | uuid | YES |  | → `PaymentMethod`.`Id` |
| `PaymentOrderId` | uuid | YES |  | → `PaymentOrder`.`Id` |
| `VoucherCampaignId` | uuid | NO |  | → `VoucherCampaign`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `VoucherCampaign`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 10 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `IsActive` | boolean | NO |  |  |
| `Code` | varchar(100) | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `Price` | integer | NO |  |  |
| `ApplyAllProductCategory` | boolean | NO |  |  |
| `SaleOrderAmountMin` | bigint | YES |  |  |
| `LimitPerSaleOrder` | boolean | NO |  |  |
| `ApplyTimeType` | integer | NO |  |  |
| `ApplyTimeStartAt` | timestamp with time zone | YES |  |  |
| `ApplyTimeEndAt` | timestamp with time zone | YES |  |  |
| `ApplyTimeExpireType` | integer | YES |  |  |
| `ApplyTimeExpireValue` | integer | YES |  |  |
| `ApplyScopeAllSite` | boolean | NO |  |  |
| `ApplyScopeAllStaff` | boolean | NO |  |  |
| `ApplyScopeAllCustomer` | boolean | NO |  |  |
| `NumberOfVoucher` | integer | NO |  |  |
| `IsAnyVoucherUsed` | boolean | NO |  |  |
| `Note` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `VoucherCampaignType` | integer | NO | 0 |  |

## Table `VoucherCampaignApplyScopeCustomer`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `VoucherCampaignId` | uuid | NO |  | → `VoucherCampaign`.`Id` |
| `CustomerId` | uuid | NO |  | → `Customer`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `VoucherCampaignApplyScopeSite`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `VoucherCampaignId` | uuid | NO |  | → `VoucherCampaign`.`Id` |
| `SiteId` | uuid | NO |  | → `Site`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `VoucherCampaignApplyScopeStaff`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `VoucherCampaignId` | uuid | NO |  | → `VoucherCampaign`.`Id` |
| `StaffId` | uuid | NO |  | → `Staff`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `VoucherCampaignPreOrder`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `VoucherCampaignId` | uuid | NO |  | → `VoucherCampaign`.`Id` |
| `PreOrderId` | uuid | NO |  | → `PreOrder`.`Id` |
| `TotalAmount` | bigint | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `VoucherCampaignProduct`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `VoucherCampaignId` | uuid | NO |  | → `VoucherCampaign`.`Id` |
| `ProductId` | uuid | NO |  | → `Product`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `VoucherCampaignProductCategory`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `VoucherCampaignId` | uuid | NO |  | → `VoucherCampaign`.`Id` |
| `ProductCategoryId` | uuid | NO |  | → `ProductCategory`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `VoucherCampaignSaleOrder`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `VoucherCampaignId` | uuid | NO |  | → `VoucherCampaign`.`Id` |
| `SaleOrderId` | uuid | NO |  | → `SaleOrder`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `TotalAmount` | bigint | NO | 0 |  |

## Table `VoucherOwner`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `OwnerType` | integer | NO |  |  |
| `OwnerId` | uuid | NO |  |  |
| `VoucherId` | uuid | NO |  | → `Voucher`.`Id` |
| `CustomerId` | uuid | YES |  | → `Customer`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `Wages`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `SalaryStructureId` | uuid | NO |  | → `SalaryStructure`.`Id` |
| `WorkingShiftId` | uuid | YES |  | → `WorkingShift`.`Id` |
| `PayRate` | bigint | NO |  |  |
| `SalarySaturday` | text | YES |  |  |
| `SalarySunday` | text | YES |  |  |
| `SalaryHoliday` | text | YES |  |  |
| `SalaryFestival` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `Ward`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Code`
- **Bảng khác FK vào đây:** 8 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Code` | integer | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `DistrictCode` | integer | NO |  | → `District`.`Code` |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `NewWardCode` | integer | YES |  | → `NewWard`.`Code` |

## Table `Warehouse`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 10 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | YES |  |  |
| `State` | integer | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `StreetAddress` | varchar(500) | NO |  |  |
| `FullAddress` | varchar(1000) | NO |  |  |
| `WardCode` | integer | YES |  | → `Ward`.`Code` |
| `DistrictCode` | integer | NO |  | → `District`.`Code` |
| `ProvinceCode` | integer | NO |  | → `Province`.`Code` |
| `SiteId` | uuid | YES |  | → `Site`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `NewProvinceCode` | integer | YES |  | → `NewProvince`.`Code` |
| `NewWardCode` | integer | YES |  | → `NewWard`.`Code` |
| `AllowNegativeInventory` | boolean | NO | false |  |

## Table `WebhookEvent`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(200) | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `WebhookListener`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 2 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `EndpointUrl` | text | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `WebhookListenerEvent`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `WebhookListenerId`, `WebhookEventId`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `WebhookListenerId` | uuid | NO |  | → `WebhookListener`.`Id` |
| `WebhookEventId` | uuid | NO |  | → `WebhookEvent`.`Id` |

## Table `WebhookPushMessage`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `WebhookListenerId` | uuid | NO |  | → `WebhookListener`.`Id` |
| `WebhookEventId` | uuid | NO |  | → `WebhookEvent`.`Id` |
| `PushedAt` | timestamp with time zone | YES |  |  |
| `FailedCount` | integer | NO |  |  |
| `Action` | text | NO |  |  |
| `Data` | text | NO |  |  |
| `LastError` | text | YES |  |  |
| `JobId` | text | YES |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `Workflow`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 28 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `TargetType` | integer | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `WorkflowState`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 30 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Code` | varchar(100) | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `TargetType` | integer | NO |  |  |
| `IsCompleteState` | boolean | NO |  |  |
| `IsHideFromAdmin` | boolean | NO |  |  |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `WorkflowStep`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `FromStateId` | uuid | YES |  | → `WorkflowState`.`Id` |
| `ToStateId` | uuid | YES |  | → `WorkflowState`.`Id` |
| `WorkflowId` | uuid | NO |  | → `Workflow`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `WorkingShift`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`
- **Bảng khác FK vào đây:** 4 liên kết (xem các bảng con trong catalog)

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `Name` | varchar(200) | NO |  |  |
| `State` | integer | NO |  |  |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |
| `CheckTimeEnd` | integer | NO | 0 |  |
| `CheckTimeStart` | integer | NO | 0 |  |
| `WorkingTimeEnd` | integer | NO | 0 |  |
| `WorkingTimeStart` | integer | NO | 0 |  |
| `SiteId` | uuid | NO | '00000000-0000-0000-0000-000000000000'::uuid | → `Site`.`Id` |

## Table `WorkingShiftSite`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `Id`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `Id` | uuid | NO |  |  |
| `WorkingShiftId` | uuid | NO |  | → `WorkingShift`.`Id` |
| `SiteId` | uuid | NO |  | → `Site`.`Id` |
| `CreateAt` | timestamp with time zone | YES |  |  |
| `CreatorId` | uuid | YES |  |  |
| `UpdateAt` | timestamp with time zone | YES |  |  |
| `UpdatorId` | uuid | YES |  |  |
| `DeleteAt` | timestamp with time zone | YES |  |  |

## Table `__EFMigrationsHistory`

- **Schema:** `public`
- **Loại:** BASE TABLE
- **Khóa chính:** `MigrationId`

| Cột | Kiểu | Nullable | Default | FK / tham chiếu |
|-----|------|----------|---------|-----------------|
| `MigrationId` | varchar(150) | NO |  |  |
| `ProductVersion` | varchar(32) | NO |  |  |

