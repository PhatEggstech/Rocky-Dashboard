# Đặc tả Cơ sở Dữ liệu và Quy tắc Nghiệp vụ Chuỗi Rocky (Unified Schema & Business Spec)

Tài liệu này tổng hợp toàn bộ cấu trúc bảng dữ liệu (Database Schema) của cả lớp Gold Layer (`rocky_dashboard`) và lớp POS gốc (`rocky_stg`), cùng với các quy tắc tính toán nghiệp vụ cốt lõi của chuỗi Rocky. 

Khi nhận được các câu hỏi của người dùng nằm ngoài các tool có sẵn, Trợ lý AI có thể tham chiếu tài liệu này để viết các câu lệnh SQL truy vấn trực tiếp thông qua `query_raw_sql_tool`.

---

## 1. Cấu trúc Database Gold Layer (Bảng cục bộ trên AI Server)

Database Gold Layer (`rocky_dashboard` trên `localhost:5432`) lưu trữ dữ liệu tổng hợp đã được làm sạch và tối ưu hóa từ các luồng POS và WMS.

### Bảng 1.1: `stores` (Thông tin cửa hàng/chi nhánh)
*   `id` (TEXT, PK): Mã định danh cửa hàng (UUID dạng chuỗi).
*   `name` (TEXT): Tên cửa hàng (ví dụ: Rocky Quận 10, Rocky Gò Vấp...).
*   `code` (TEXT): Mã cửa hàng (ví dụ: ROCKY_Q10, ROCKY_GV...).
*   `pos_site_id` (TEXT): ID tương ứng trong bảng `Site` của POS.

### Bảng 1.2: `daily_sales` (Báo cáo doanh số bán hàng hàng ngày)
*   `site_id` (TEXT, PK): ID cửa hàng (nối với `stores.id`).
*   `d` (TEXT, PK): Ngày bán hàng dạng chuỗi (`YYYY-MM-DD`).
*   `revenue` (DOUBLE PRECISION): Doanh thu thực nhận (Tiền thực thu từ khách hàng, đã trừ các đơn hoàn trả tiền).
*   `orders_n` (INTEGER): Tổng số lượng đơn hàng được giao thành công trong ngày.
*   `cogs` (DOUBLE PRECISION): Giá vốn hàng bán (Cost of Goods Sold).
*   `unique_customers` (INTEGER): Số lượng khách hàng mua sắm không trùng lặp trong ngày.
*   `subtotal` (DOUBLE PRECISION): Doanh số đặt hàng (Tổng giá trị sản phẩm của các đơn hàng được duyệt thành công, đã khấu trừ các đơn trả lại hàng).

### Bảng 1.3: `inventory_wms` (Dữ liệu tồn kho chi tiết)
*   `product_item_id` (TEXT, PK): ID sản phẩm chi tiết (variant/SKU).
*   `sku` (TEXT): Mã SKU của sản phẩm.
*   `name` (TEXT): Tên sản phẩm.
*   `category` (TEXT): Nhóm hàng (ví dụ: Gọng kính, Tròng kính, Kính mát, Phụ kiện...).
*   `stock_level` (DOUBLE PRECISION): Số lượng tồn kho hiện tại.
*   `stock_cover_days` (DOUBLE PRECISION): Số ngày phủ kho ước tính (Số ngày tồn kho có thể đáp ứng dựa trên tốc độ bán hàng trung bình). Tối đa là 3650 ngày.
*   `dead_stock_days` (DOUBLE PRECISION): Số ngày hàng chết (Số ngày liên tục sản phẩm không phát sinh bất kỳ giao dịch bán ra nào).
*   `status` (TEXT): Trạng thái tồn kho (`normal` hoặc `dead_stock` nếu `dead_stock_days > 90`).
*   `updated_at` (TEXT): Thời gian đồng bộ cuối cùng.

### Bảng 1.4: `daily_picker_performance` (Hiệu suất soạn hàng của nhân viên kho WMS)
*   `staff_id` (TEXT, PK): ID nhân viên soạn hàng (Picker).
*   `staff_name` (TEXT): Tên nhân viên soạn hàng.
*   `d` (TEXT, PK): Ngày soạn hàng dạng chuỗi (`YYYY-MM-DD`).
*   `store_id` (TEXT, PK): ID cửa hàng/kho chứa hàng.
*   `orders_picked` (INTEGER): Số lượng đơn hàng đã soạn hoàn tất trong ngày.
*   `items_picked` (DOUBLE PRECISION): Số lượng sản phẩm đã soạn hoàn tất trong ngày.
*   `total_pick_time` (DOUBLE PRECISION): Tổng thời gian soạn hàng trong ngày (tính bằng giây).
*   `avg_pick_time` (DOUBLE PRECISION): Thời gian soạn hàng trung bình cho mỗi đơn hàng (tính bằng giây/đơn).

### Bảng 1.5: `debt_report` (Báo cáo công nợ đại lý B2B)
*   `customer_name` (TEXT): Tên đại lý B2B.
*   `previous_balance` (DOUBLE PRECISION): Số dư nợ cũ đầu kỳ.
*   `debt_amount` (DOUBLE PRECISION): Dư nợ mới phát sinh trong kỳ.
*   `total_receive_amount` (DOUBLE PRECISION): Số tiền nợ đã thu hồi được trong kỳ (khách đã trả).
*   `current_balance` (DOUBLE PRECISION): Số dư nợ hiện tại cuối kỳ (Giá trị âm biểu thị khách hàng đang nợ Rocky).
*   `start_at` (TEXT): Ngày bắt đầu kỳ báo cáo công nợ.
*   `end_at` (TEXT): Ngày kết thúc kỳ báo cáo công nợ.

---

## 2. Cấu trúc Database POS Gốc (Database `rocky_stg` trên `10.39.93.117`)

Khi cần tính toán các chỉ số chi tiết chưa được tổng hợp trong Gold Layer, AI có thể viết câu lệnh SQL truy cập trực tiếp các bảng nguồn của POS.

### Bảng 2.1: `Order` (Bảng đơn hàng gốc)
*   `Id` (UUID/TEXT): Khóa chính đơn hàng.
*   `ProductAmount` (NUMERIC): Giá trị tổng sản phẩm trong đơn hàng.
*   `PaidAmount` (NUMERIC): Số tiền thực tế khách đã thanh toán cho đơn hàng.
*   `PaymentState` (INTEGER): Trạng thái thanh toán (Giá trị `3` = Đã thanh toán hoàn tất).
*   `CancelAt` (TIMESTAMP): Thời gian hủy đơn hàng (Nếu NULL là đơn hoạt động).
*   `DeleteAt` (TIMESTAMP): Thời gian xóa đơn hàng (Nếu NULL là đơn hoạt động).
*   `IssueAt` (TIMESTAMP): Ngày phát hành đơn hàng.
*   `WarehouseId` (UUID/TEXT): ID kho xuất hàng (Nối với `Warehouse.Id`).
*   `CustomerId` (UUID/TEXT): ID khách hàng (Nối với `Customer.Id`).
*   `ExchangeParentOrderId` (UUID/TEXT): ID đơn hàng gốc của sản phẩm cần đổi trả. **Nếu trường này khác NULL, đơn hàng này là đơn làm lại kính (Remake Order)**.

### Bảng 2.2: `Warehouse` (Kho hàng)
*   `Id` (UUID/TEXT): Khóa chính.
*   `SiteId` (UUID/TEXT): ID chi nhánh/cửa hàng tương ứng (Nối với `Site.Id`).

### Bảng 2.3: `Site` (Chi nhánh)
*   `Id` (UUID/TEXT): Khóa chính.
*   `Name` (TEXT): Tên chi nhánh.
*   `DeleteAt` (TIMESTAMP): Thời gian xóa (Nếu NULL là hoạt động).

---

## 3. Công thức Nghiệp vụ Cốt lõi của Rocky

### 3.1. Doanh thu (Revenue) vs Doanh số (Subtotal)
*   **Doanh thu (Revenue):** Là số tiền thực nhận từ các đơn hàng được giao thành công.
    $$\text{Doanh thu} = \text{SUM}(o.\text{ProductAmount}) \text{ của tất cả các đơn o (CancelAt IS NULL và DeleteAt IS NULL)}$$
*   **Doanh số (Subtotal):** Là tổng giá trị thực thu của các đơn hàng có trạng thái thanh toán hoàn tất.
    $$\text{Doanh số} = \text{SUM}(o.\text{PaidAmount}) \text{ của các đơn o có o.PaymentState = 3 (CancelAt IS NULL và DeleteAt IS NULL)}$$

### 3.2. Biên Lợi nhuận Gộp (GPM) và Biên Lợi nhuận Ròng Proxy (NPM)
*   **Biên Lợi nhuận Gộp (GPM %):**
    $$\text{GPM} = \frac{\text{Revenue} - \text{COGS}}{\text{Revenue}} \times 100$$
*   **Biên Lợi nhuận Ròng Proxy (NPM %):**
    Rocky sử dụng ước lượng chi phí vận hành (Opex Proxy) bằng **12% Doanh số (Subtotal)**.
    $$\text{Opex} = \text{Subtotal} \times 0.12$$
    $$\text{NPM} = \frac{\text{Revenue} - \text{COGS} - \text{Opex}}{\text{Revenue}} \times 100$$

### 3.3. Các Chỉ số Bán hàng khác
*   **ATV (Average Transaction Value - Giá trị trung bình đơn hàng):**
    $$\text{ATV} = \frac{\text{Revenue}}{\text{orders\_n}}$$
*   **UPT (Units Per Transaction - Số sản phẩm trung bình mỗi đơn):** Được tính dựa trên số lượng sản phẩm chi tiết trong đơn hàng.
*   **RPS (Revenue Per Staff - Doanh thu trên đầu nhân sự):**
    $$\text{RPS} = \frac{\text{Revenue}}{\text{Số nhân sự tại cửa hàng (mặc định là 12 nếu trống)}}$$
*   **Tỷ lệ làm lại kính (Remake Rate %):**
    $$\text{Remake Rate} = \frac{\text{Số đơn làm lại (ExchangeParentOrderId IS NOT NULL)}}{\text{Tổng số đơn hàng}} \times 100$$
    *(Truy vấn trực tiếp từ POS `Order` table)*

---

## 4. Hướng dẫn viết SQL thô (SQL Query Guidelines)

Khi viết câu lệnh SQL chạy qua `query_raw_sql_tool` hoặc `query_remake_rate`, AI cần tuyệt đối tuân thủ các quy tắc sau:

1.  **Xử lý Múi giờ (Timezone):**
    Toàn bộ các trường TIMESTAMP của hệ thống (như `IssueAt`, `CompleteAt`, `ApproveAt`) lưu ở UTC. Phải chuyển đổi sang múi giờ Việt Nam (`Asia/Ho_Chi_Minh`) trước khi so sánh hoặc làm tròn ngày bằng cú pháp:
    ```sql
    (o."IssueAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
    ```
2.  **Lọc dữ liệu rác (Soft Delete):**
    Với tất cả các bảng lấy trực tiếp từ database POS (`rocky_stg`), bắt buộc phải thêm điều kiện lọc bản ghi đã xóa:
    ```sql
    WHERE "DeleteAt" IS NULL
    ```
3.  **Tránh chia cho 0 (Divide-by-zero):**
    Sử dụng `NULLIF(biểu_thức, 0)` khi thực hiện phép chia để tránh crash hệ thống:
    ```sql
    (SUM(remake_orders)::float / NULLIF(SUM(total_orders), 0)) * 100
    ```
4.  **Giới hạn kết quả (LIMIT):**
    Để tránh làm quá tải bộ nhớ, luôn giới hạn số lượng dòng trả về (tối đa 100 dòng) đối với các câu lệnh Select danh sách chi tiết:
    ```sql
    LIMIT 50
    ```
