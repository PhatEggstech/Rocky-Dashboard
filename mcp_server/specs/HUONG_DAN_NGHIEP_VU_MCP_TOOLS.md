# HƯỚNG DẪN NGHIỆP VỤ VÀ CÁCH DÙNG MCP TOOLS — ROCKY LENS DASHBOARD

> **QUAN TRỌNG**: Đọc tài liệu này TRƯỚC KHI query bất kỳ dữ liệu nào về doanh số, doanh thu, đơn trả.

---

## 1. ĐỊNH NGHĨA THUẬT NGỮ CỐT LÕI

### 1.1 Doanh Số vs Doanh Thu — KHÔNG PHẢI CÙNG MỘT THỨ

| Thuật ngữ | Định nghĩa | Field tương ứng |
|-----------|-----------|----------------|
| **Doanh số gộp (Gross Sales)** | Tổng tiền hàng trước khi trừ đơn trả | `OrderItem.SubTotalIncludeDiscount` |
| **Doanh số thực tế / Net Sales** | Doanh số gộp đã trừ đi giá trị đơn hàng hoàn trả | `daily_sales.subtotal` = Gross - Returns |
| **Doanh thu (Revenue)** | Trong hệ thống này = Net Sales (đã trừ đơn trả) | `daily_sales.revenue` = `daily_sales.subtotal` |

> ⚠️ **LƯU Ý CỰC KỲ QUAN TRỌNG**: `daily_sales.subtotal` và `daily_sales.revenue` **ĐÃ LÀ NET** (đã trừ đơn trả rồi). KHÔNG được trừ thêm lần nữa.

### 1.2 Loại Đơn Hàng (Order.Type)

Hệ thống **CHỈ báo cáo Type = 1** (đơn bán thường tại cửa hàng).

| Type | Loại | Có trong báo cáo? |
|------|------|-------------------|
| 1 | Đơn bán thường (tại cửa hàng) | ✅ CÓ |
| 2 | Đơn B2B qua app/web đại lý | ❌ KHÔNG (đã loại trừ) |

### 1.3 Phân Loại Khách Hàng (is_hmk)

| is_hmk | Loại khách | Nguồn gốc |
|--------|-----------|-----------|
| `TRUE` | **HMK / Đại lý B2B** | `Customer.IsHmkCustomer = TRUE` |
| `FALSE` | **Khách lẻ / B2C** | `Customer.IsHmkCustomer = FALSE` hoặc NULL |

### 1.4 Đơn Trả (Returns)

- Đơn trả được tính vào **tháng mà `ReturnOrder.CompleteAt` xảy ra** (không phụ thuộc tháng đơn gốc)
- `daily_sales.subtotal` = Gross Sales - Return Amount (đã trừ sẵn)
- `monthly_returns` lưu tổng đơn trả theo tháng theo cửa hàng

---

## 2. CÁC MCP TOOLS VÀ CÁCH DÙNG ĐÚNG

### 2.1 `get_sales_by_customer_type(date_from, date_to)`

**Mục đích**: Phân loại doanh số theo HMK vs Khách lẻ.

**Dữ liệu trả về — CÁCH ĐỌC ĐÚNG**:

```
summary:
  hmk_subtotal    → Doanh số NET của HMK (đã trừ đơn trả)
  other_subtotal  → Doanh số NET của Khách lẻ (đã trừ đơn trả)
  total_subtotal  → Tổng doanh số NET (đã trừ đơn trả)
  hmk_orders      → Số đơn bán HMK
  other_orders    → Số đơn bán Khách lẻ
  hmk_units       → Số sản phẩm HMK
  other_units     → Số sản phẩm Khách lẻ

return_orders → Tổng số đơn trả trong kỳ (từ monthly_returns)
```

> ⚠️ **TUYỆT ĐỐI KHÔNG** lấy `return_orders` rồi trừ vào `subtotal` — sẽ tính SAI vì subtotal đã net rồi!

**Ví dụ kết quả đúng tháng 4/2026**:
- HMK net: 2,976,279,250đ | 11,510 đơn
- Khách lẻ net: 4,252,047,122đ | 11,151 đơn
- Tổng net: 7,228,326,372đ | 22,661 đơn

### 2.2 `get_gross_net_sales(date_from, date_to)`

**Mục đích**: Xem tổng gross và net theo chuỗi ngày.

**Dữ liệu trả về**:
```
gross_sales     → Doanh số gộp (chưa trừ đơn trả)
net_sales       → Doanh số thực (đã trừ đơn trả) = gross - returns
return_amount   → Tổng giá trị đơn trả
return_count    → Số đơn trả
```

### 2.3 `get_revenue(date_from, date_to, ...)`

**Dữ liệu trả về**: Revenue trong hệ thống = Net Sales (đã trừ đơn trả).

### 2.4 `get_orders(date_from, date_to, ...)`

Chỉ trả về đơn Type=1. Không bao gồm đơn B2B Type=2.

---

## 3. CÔNG THỨC TÍNH CHUẨN

### 3.1 Doanh số Net theo nhóm khách
```
Net_HMK     = SUM(daily_sales.subtotal) WHERE is_hmk = TRUE
Net_Khachlẻ = SUM(daily_sales.subtotal) WHERE is_hmk = FALSE
Net_Total   = Net_HMK + Net_Khachlẻ
```

### 3.2 Doanh số Gross (nếu cần tính ngược)
```
Gross = Net + Returns (từ monthly_returns hoặc return_orders trong get_sales_by_customer_type)
```

### 3.3 Tỷ lệ đóng góp
```
HMK%     = Net_HMK / Net_Total × 100
Khachlẻ% = Net_Khachlẻ / Net_Total × 100
```

### 3.4 Giá trị trung bình mỗi đơn (ATV)
```
ATV_HMK     = Net_HMK / hmk_orders
ATV_Khachlẻ = Net_Khachlẻ / other_orders
```

---

## 4. CÁC CÂU HỎI THƯỜNG GẶP VÀ CÁCH TRẢ LỜI ĐÚNG

### Q: "Doanh số tháng X/YYYY là bao nhiêu?"
→ Dùng `get_sales_by_customer_type` hoặc `get_gross_net_sales`
→ Báo cáo `summary.total_subtotal` = Doanh số NET (sau trừ đơn trả)

### Q: "Doanh số HMK vs Khách lẻ?"
→ Dùng `get_sales_by_customer_type`
→ `hmk_subtotal` = HMK net, `other_subtotal` = Khách lẻ net
→ KHÔNG trừ thêm đơn trả nữa

### Q: "Doanh số gộp (gross) là bao nhiêu?"
→ Gross = Net + return_amount
→ Hoặc dùng SQL: `SELECT SUM(oi."SubTotalIncludeDiscount") FROM "OrderItem" oi JOIN "Order" o...`

### Q: "Số đơn trả và giá trị đơn trả?"
→ Dùng `get_gross_net_sales` (có `return_count`, `return_amount`)
→ Hoặc query `monthly_returns` table

### Q: "Doanh thu vs Doanh số khác nhau thế nào?"
→ Trong hệ thống Rocky: **Doanh thu = Doanh số Net** (cùng một số)
→ `daily_sales.revenue` = `daily_sales.subtotal` = Net Sales
→ Chỉ khác nhau nếu user muốn gross (chưa trừ đơn trả)

---

## 5. CẤU TRÚC BẢNG DASHBOARD DATABASE

### `daily_sales` — Bảng trung tâm
| Cột | Kiểu | Ý nghĩa |
|-----|------|---------|
| `store_id` | TEXT | ID cửa hàng |
| `d` | TEXT | Ngày (YYYY-MM-DD) |
| `is_hmk` | BOOLEAN | TRUE = đại lý B2B, FALSE = khách lẻ |
| `subtotal` | FLOAT | **NET Sales** = Gross - Returns (ĐÃ TRỪ ĐƠN TRẢ) |
| `revenue` | FLOAT | = subtotal (cùng giá trị) |
| `orders_n` | INT | Số đơn bán |
| `completed_orders_n` | INT | Số đơn hoàn thành |
| `units_sold` | INT | Số sản phẩm bán |
| `cogs` | FLOAT | Giá vốn |
| `gross_profit` | FLOAT | Lợi nhuận gộp = subtotal - cogs |
| `avg_order_value` | FLOAT | Giá trị trung bình mỗi đơn |
| `unique_customers` | INT | Số khách hàng duy nhất |

### `monthly_returns` — Đơn trả theo tháng/cửa hàng
| Cột | Ý nghĩa |
|-----|---------|
| `store_id` | ID cửa hàng |
| `year_month` | Tháng (YYYY-MM) |
| `return_count` | Tổng số đơn trả trong tháng |
| `return_amount` | Tổng giá trị đơn trả |

> Lưu ý: `monthly_returns` KHÔNG phân tách HMK/Khách lẻ — chỉ có tổng theo cửa hàng.

---

## 6. SỐ LIỆU KIỂM CHỨNG THÁNG 4/2026 (CHUẨN)

| Chỉ số | HMK (B2B) | Khách lẻ | Tổng |
|--------|-----------|----------|------|
| Doanh số gộp | ~3,002 tỷ | ~4,455 tỷ | ~7,457 tỷ |
| Giá trị đơn trả | ~25.9 triệu | ~202.9 triệu | ~228.8 triệu |
| **Doanh số NET** | **2,976,279,250đ** | **4,252,047,122đ** | **7,228,326,372đ** |
| Số đơn bán | 11,510 | 11,151 | 22,661 |
| Số đơn trả | 128 | 496 | 624 |
| ATV (net) | ~258,583đ | ~381,145đ | — |

---

## 7. LỖI THƯỜNG GẶP — TRÁNH

| Lỗi | Nguyên nhân | Cách đúng |
|-----|-------------|-----------|
| Net HMK = 0 hoặc âm | Trừ đơn trả 2 lần | `subtotal` đã là net, không trừ nữa |
| Net Total = ~5,703 tr | Lấy gross rồi trừ toàn bộ return_amount vào sai chỗ | Dùng `subtotal` trực tiếp |
| HMK đơn trả = 0 | `monthly_returns` không phân HMK/khách lẻ | Đây là giới hạn của bảng, không query được tách riêng |
| Số đơn quá lớn (>30,000) | Đang lấy cả Type=2 | `daily_sales` đã filter Type=1 rồi |

---

## 8. VÍ DỤ QUERY SQL ĐÚNG

### Doanh số NET theo tháng và loại khách
```sql
SELECT 
    LEFT(d, 7) AS year_month,
    is_hmk,
    SUM(subtotal) AS net_sales,
    SUM(orders_n) AS total_orders,
    SUM(units_sold) AS total_units
FROM daily_sales
WHERE d BETWEEN '2026-04-01' AND '2026-04-30'
GROUP BY year_month, is_hmk
ORDER BY year_month, is_hmk;
```

### Doanh số Gross (cần tính ngược từ net + returns)
```sql
-- Gross = Net + Returns (returns đã được trừ khỏi subtotal lúc sync)
-- Không thể query gross trực tiếp từ daily_sales
-- Dùng POS raw SQL nếu cần gross chính xác
```

### Trend doanh số ngày theo loại khách
```sql
SELECT d,
    SUM(CASE WHEN is_hmk THEN subtotal ELSE 0 END) AS hmk_net,
    SUM(CASE WHEN NOT is_hmk THEN subtotal ELSE 0 END) AS retail_net,
    SUM(subtotal) AS total_net,
    SUM(orders_n) AS total_orders
FROM daily_sales
WHERE d BETWEEN '2026-04-01' AND '2026-04-30'
GROUP BY d ORDER BY d;
```

---

_Tài liệu này được tạo để hỗ trợ AI agent hiểu đúng nghiệp vụ Rocky Lens Dashboard._  
_Cập nhật: 2026-06-16. Nếu có thắc mắc về logic, đọc thêm `DASHBOARD_FORMULAS.md`._
