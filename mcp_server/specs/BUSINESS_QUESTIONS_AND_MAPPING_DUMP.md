
# FILE: business_questions_for_leader.xlsx

## SHEET: 1. Ban hang (Sales) (9 rows, 4 cols)

| STT | Cau hoi | Ly do can hoi | Ghi chu (Leader tra loi) |
| --- | --- | --- | --- |
| 1 | Quy trinh don hang tu luc khach vao den khi thanh toan xong gom nhung buoc nao? (Walk-in > Eye exam > Chon gong > Do kinh > Thanh toan > Giao kinh) | Hien tai dung proxy orders*1.6 cho walk-in vi khong co data that |  |
| 2 | Khi nao don duoc tinh la hoan thanh - ApproveAt hay CompleteAt? Truong hop nao don Approve roi nhung khong Complete? | Lien quan doanh so vs doanh thu. Hien co 425 don Approve nhung chua Complete |  |
| 3 | Don hang co bao nhieu loai? (ban le, ban buon B2B, ban online, tra gop, khuyen mai...) Phan biet bang truong nao? | Can filter dung loai don cho tung metric |  |
| 4 | Phi ship (ShippingFee) tinh vao doanh thu hay khong? Truong ApproveAt va CompleteAt cua ShippingFee nghia gi? | Leader da mention truoc do nhung chua ro logic |  |
| 5 | PaymentOrder.DocumentType co nhung gia tri nao? (1=Phieu thu, con gi nua?) | Hien chi filter DocumentType=1, can biet cac loai khac |  |
| 6 | Don huy (CancelAt) co can tinh vao bao cao khong? Khi nao don bi huy? | De loai bo don huy khoi thong ke chinh xac |  |
| 7 | Mot don hang co the co nhieu PaymentOrder khong? (tra nhieu lan, tra gop) | Anh huong den cach tinh doanh thu theo ngay |  |
| 8 | Voucher/Chiet khau nam giam doanh thu hay ghi nhan rieng? Truong nao trong POS? | PaymentMethod co Chiet khau nam va Voucher khach hang - can biet cach xu ly |  |


## SHEET: 2. Cong no B2B (Debt) (9 rows, 4 cols)

| STT | Cau hoi | Ly do can hoi | Ghi chu (Leader tra loi) |
| --- | --- | --- | --- |
| 1 | Khach B2B (dai ly) khac khach le bang truong nao? Co truong CustomerType hay phai dung CustomerGroup? | Can tach dashboard B2C vs B2B |  |
| 2 | DebtReport.PreviousBalance am (-135,000) nghia la khach no hay cua hang no khach? | Data thuc te thay gia tri am, can hieu chieu no |  |
| 3 | Chu ky bao cao cong no la gi? (daily? weekly? monthly?) Leader muon xem theo ky nao? | DebtReport co StartAt/EndAt daily, nhung leader co the muon xem theo thang |  |
| 4 | Ty le thu hoi no (RecoverDebtRate) tinh the nao? Muc tieu thu hoi bao nhieu %? | Can biet KPI target de hien canh bao |  |
| 5 | Khach no qua han bao nhieu ngay thi canh bao? Co muc do (xanh/vang/do)? | De lam alert tren dashboard |  |
| 6 | Cong no co phan biet theo loai (cong no hang hoa vs cong no dich vu)? | Bao cao cong no can tach loai hay gop? |  |
| 7 | Ai la nguoi duyet thanh toan cong no? Quy trinh thu no nhu the nao? | Hieu workflow de thiet ke dashboard phu hop |  |
| 8 | Co tinh lai/phat cho no qua han khong? | Can biet co truong nao trong DB luu lai/phat |  |


## SHEET: 3. Nhan su (Staff) (9 rows, 4 cols)

| STT | Cau hoi | Ly do can hoi | Ghi chu (Leader tra loi) |
| --- | --- | --- | --- |
| 1 | Moi cua hang co bao nhieu nhan vien? So lieu lay tu dau (bang Staff)? Co nhan vien part-time khong? | Hien default = 12, can so that cho Revenue/Staff |  |
| 2 | Hoa hong (commission) tinh theo doanh thu hay doanh so? Cong thuc? | POS co bang Commission nhung chua dung |  |
| 3 | KPI cho nhan vien ban hang la gi? (doanh thu/ngay, so don/ngay, ty le chot?) | De hien thi performance scoring |  |
| 4 | Nhan vien lam viec theo ca nhu the nao? (full-time, part-time, ca sang/chieu) | Anh huong cach tinh productivity/hour |  |
| 5 | Co danh gia nhan vien hang thang khong? Tieu chi nao? | De lam bang xep hang nhan vien |  |
| 6 | StaffId trong Order la nguoi ban hay nguoi tao don? Co nhieu nguoi phuc vu 1 don khong? | Hien quy het doanh thu cho 1 StaffId, co the sai |  |
| 7 | Nhan vien moi vao bao lau thi duoc tinh KPI? Co thoi gian thu viec? | De loai nhan vien moi khoi bang xep hang |  |
| 8 | Target doanh thu cho tung nhan vien la bao nhieu? Ai dat? | Can data target de tinh % dat chi tieu |  |


## SHEET: 4. Ton kho (Inventory) (9 rows, 4 cols)

| STT | Cau hoi | Ly do can hoi | Ghi chu (Leader tra loi) |
| --- | --- | --- | --- |
| 1 | San pham gong kinh, trong kinh, phu kien - phan loai bang ProductCategory hay truong khac? | Can hien inventory theo nhom dung |  |
| 2 | Dead stock (hang chet) dinh nghia the nao? Bao nhieu ngay khong ban la dead stock? (30? 60? 90?) | Hien dung 90 ngay nhung chua confirm |  |
| 3 | Khi nao thi can dat hang them? Co muc ton kho toi thieu (reorder point) cho tung SKU khong? | De lam alert khi sap het hang |  |
| 4 | Luan chuyen hang giua cac cua hang (transfer) co pho bien khong? Logic nao? | WMS co InventoryHistory nhung chua phan biet transfer vs sale |  |
| 5 | Hang ton kho tinh theo gia von (CostPrice) hay gia ban? Gia von cap nhat bao lau 1 lan? | Anh huong tinh Inventory Value va GMROI |  |
| 6 | Co san pham nao theo mua (seasonal)? Vi du gong mat troi chi ban he? | De phan tich xu huong ton kho theo mua |  |
| 7 | San pham loi/hu tinh vao ton kho hay tach rieng? | Can biet co trang thai san pham (tot/hu/bao hanh) |  |
| 8 | Warehouse trong WMS va Warehouse trong POS co map 1-1 khong? | Hien dung WarehouseId de map store, can xac nhan |  |


## SHEET: 5. Khach hang (Customer) (10 rows, 4 cols)

| STT | Cau hoi | Ly do can hoi | Ghi chu (Leader tra loi) |
| --- | --- | --- | --- |
| 1 | Khach quay lai (returning) dinh nghia the nao? Mua lan 2 trong bao lau? (30 ngay? 6 thang? 1 nam?) | Kinh mat la san pham mua it lan/nam |  |
| 2 | Co chay campaign marketing nao tren POS khong? (voucher, khuyen mai, giam gia theo mua) | Bang Campaign/Promotion trong POS chua dung |  |
| 3 | Target doanh thu hang thang cua moi cua hang la bao nhieu? Ai nhap? | Hien khong co data target, can cho phan % dat target |  |
| 4 | Khach VIP/than thiet phan loai the nao? Co chuong trinh loyalty/tich diem? | De lam phan khuc khach hang chinh xac hon |  |
| 5 | CSAT (hai long khach hang) do bang cach nao? Zalo survey? Google review? Truc tiep tai cua hang? | Hien chi co proxy tu ty le tra hang |  |
| 6 | Khach mua kinh trung binh bao lau mua lai? (1 nam? 2 nam?) | De tinh Customer Lifetime Value dung |  |
| 7 | Co phan biet khach online vs offline? Kenh ban hang nao quan trong nhat? | De lam bao cao channel mix |  |
| 8 | Remake (lam lai kinh) xay ra khi nao? Do sai so do hay khach doi y? Ti le chap nhan? | Hien dung proxy MeasurementTicket trong 14 ngay, chua chinh xac |  |
| 9 | Co thu thap so dien thoai/email khach de remarketing khong? Ti le co thong tin? | Anh huong kha nang lam retention campaign |  |


# FILE: mapping_source_code.xlsx

## SHEET: 1. DOANH THU (Revenue) (14 rows, 6 cols)

| # | Leader (C#) | Code (pos_sync.py) | Database Table.Field | Giống/Khác | Ghi chú |
| --- | --- | --- | --- | --- | --- |
|  | DOANH THU (Revenue) |  |  |  |  |
|  | Leader formula: | revenue_sql trong sync_daily_sales() |  |  |  |
| 1 | PaymentOrderItem .Where(...) .Sum(x => x.PaidAmount) | FROM "PaymentOrderItem" poi JOIN "PaymentOrder" po   ON po."Id" = poi."PaymentOrderId" ... SELECT SUM(poi."PaidAmount") | PaymentOrderItem.PaidAmount PaymentOrder (join) | GIỐNG |  |
| 2 | x.PaymentOrder.CompleteAt != null | WHERE po."CompleteAt" IS NOT NULL | PaymentOrder.CompleteAt | GIỐNG |  |
| 3 | x.PaymentOrder.CancelAt == null | AND po."CancelAt" IS NULL | PaymentOrder.CancelAt | GIỐNG |  |
| 4 | x.PaymentOrder.DocumentType == Receive | AND po."DocumentType" = 1 | PaymentOrder.DocumentType (1 = Phiếu thu / Receive) | GIỐNG |  |
| 5 | x.PaidAmount > 0 | AND poi."PaidAmount" > 0 | PaymentOrderItem.PaidAmount | GIỐNG |  |
| 6 | x.PaymentOrder.IssueAt >= From && x.PaymentOrder.IssueAt <= To | Không filter date range (lấy tất cả, group by ngày) | PaymentOrder.IssueAt | KHÁC (không ảnh hưởng) | Code sync ALL data, API filter theo date sau |
| 7 | (không có) | AND po."DeleteAt" IS NULL AND poi."DeleteAt" IS NULL | PaymentOrder.DeleteAt PaymentOrderItem.DeleteAt | THÊM | An toàn: loại record đã xóa mềm |
| 8 | (không có) | AND po."IssueAt" > '2020-01-01' | PaymentOrder.IssueAt | THÊM | Loại giá trị -infinity trong DB |
| 9 | (không có) | LEFT JOIN "Order" o   ON o."Id" = poi."OrderId" LEFT JOIN "Warehouse" w   ON w."Id" = o."WarehouseId" | Order.WarehouseId Warehouse.SiteId | THÊM | Chỉ để GROUP BY cửa hàng (store_id) |
|  | Kết luận: Logic core GIỐNG 100% | Những cái thêm không thay đổi tổng số | Đã verify: 816,176,000 = 816,176,000 |  |  |


## SHEET: 2. DOANH SỐ (Subtotal) (10 rows, 6 cols)

| # | Leader (ghi chú) | Code (pos_sync.py) | Database Table.Field | Nguồn | Ghi chú |
| --- | --- | --- | --- | --- | --- |
|  | DOANH SỐ (Subtotal) |  |  |  |  |
|  | Leader KHÔNG có formula C# | subtotal_sql trong sync_daily_sales() |  |  |  |
| 1 | "Phí ship không tính vào doanh số" | SUM(oi."SubTotalIncludeDiscount") (đã trừ discount, không có ship) | OrderItem.SubTotalIncludeDiscount | Ghi chú leader | SubTotal = giá hàng sau chiết khấu, không ship |
| 2 | "ApproveAt is not null = thu mới đúng hàng" | WHERE o."ApproveAt" IS NOT NULL | Order.ApproveAt | Ghi chú leader | Đơn chưa Approve không tính doanh số |
| 3 | (suy ra từ logic) | GROUP BY (o."ApproveAt" AT TIME ZONE 'Asia/Ho_Chi_Minh')::date | Order.ApproveAt | Suy ra | Doanh số theo ngày duyệt đơn |
| 4 | (không có) | JOIN "OrderItemGroup" oig   ON oig."Id" = oi."OrderItemGroupId" JOIN "Order" o   ON o."Id" = oig."OrderId" | OrderItem → OrderItemGroup → Order | Schema POS | Quan hệ OrderItem không trực tiếp với Order |
| 5 | (không có) | AND o."DeleteAt" IS NULL AND oi."DeleteAt" IS NULL | Order.DeleteAt OrderItem.DeleteAt | An toàn | Loại record đã xóa |
|  | Cần leader confirm: | Có formula C# cho doanh số không? |  |  |  |


## SHEET: 3. SO SÁNH Revenue vs Subtotal (11 rows, 3 cols)

|  | DOANH THU (Revenue) | DOANH SỐ (Subtotal) |
| --- | --- | --- |
| Ý nghĩa | Tiền THỰC NHẬN từ khách hàng | Giá trị HÀNG HÓA đã duyệt (không ship) |
| Công thức | SUM(PaymentOrderItem.PaidAmount) | SUM(OrderItem.SubTotalIncludeDiscount) |
| Bảng chính | PaymentOrderItem + PaymentOrder | OrderItem + OrderItemGroup + Order |
| Filter thời gian | PaymentOrder.IssueAt (ngày phát hành phiếu thu) | Order.ApproveAt (ngày duyệt đơn) |
| Bao gồm Ship? | CÓ (nếu khách trả ship thì nằm trong PaidAmount) | KHÔNG (SubTotalIncludeDiscount chỉ là tiền hàng) |
| Bao gồm Voucher? | KHÔNG (Voucher giảm PaidAmount thực nhận) | ĐÃ TRỪ (SubTotal "IncludeDiscount" = sau CK) |
| DocumentType |  | Không dùng (lấy từ Order trực tiếp) |
| Khi nào khác nhau? | Khách trả góp: Revenue < Subtotal (chỉ nhận 1 phần) | Khách trả góp: Subtotal = full (giá trị đơn đầy đủ) |
| Ví dụ (80K hàng, 20K ship, trả 60K) | Revenue = 60,000 (tiền khách thực trả) | Subtotal = 80,000 (giá trị hàng, không ship) |
| Leader có formula? | CÓ (C# code chính xác) | KHÔNG (suy ra từ ghi chú) |


## SHEET: 4. DATA FLOW (13 rows, 5 cols)

| Bước | Mô tả | Source | Target | File code |
| --- | --- | --- | --- | --- |
|  | DOANH THU |  |  |  |
| 1 | Query từ POS PostgreSQL (remote: app.riviu.com.vn) | PaymentOrderItem + PaymentOrder (rocky_dev database) | Kết quả trong memory (revenue_map dict) | pos_sync.py revenue_sql |
| 2 | Ghi vào Dashboard PostgreSQL (local: localhost:5432) | revenue_map[(site_id, date)] | daily_sales.revenue (rocky_dashboard DB) | pos_sync.py sync_daily_sales() |
| 3 | API đọc từ Dashboard PG trả về frontend | daily_sales.revenue (filter by date range) | JSON response {"scorecards": {"revenue": ...}} | react_logic.py executive_summary_payload() |
|  | DOANH SỐ |  |  |  |
| 1 | Query từ POS PostgreSQL | OrderItem.SubTotalIncludeDiscount + OrderItemGroup + Order | Kết quả trong memory (subtotal_map dict) | pos_sync.py subtotal_sql |
| 2 | Ghi vào Dashboard PostgreSQL | subtotal_map[(site_id, date)] | daily_sales.subtotal (rocky_dashboard DB) | pos_sync.py sync_daily_sales() |
| 3 | API đọc (chưa hiển lên UI) | daily_sales.subtotal | Chưa expose ra API (cần thêm vào payload) | react_logic.py (CẦN UPDATE) |
|  | CÔNG NỢ |  |  |  |
| 1 | Query từ POS PostgreSQL | DebtReport table (rocky_dev database) | Kết quả trong memory | pos_sync.py sync_debt_report() |
| 2 | Ghi vào Dashboard PostgreSQL | DebtReport rows | debt_report table (rocky_dashboard DB) | pos_sync.py sync_debt_report() |
| 3 | API đọc trả về frontend | debt_report (filter by date) | JSON response {"debt_report": [...]} | react_logic.py b2b_payload() |


## SHEET: 5. FILES MAP (14 rows, 4 cols)

| File | Chức năng | Quan hệ | Ghi chú |
| --- | --- | --- | --- |
|  | BACKEND (Python) |  |  |
| executive_dashboard/app/db.py | Kết nối PostgreSQL pool + DDL tạo bảng | get_conn() / put_conn() được dùng bởi tất cả file khác | DASHBOARD_PG_DSN env var |
| executive_dashboard/app/pos_sync.py | Sync data từ POS (remote) vào Dashboard PG (local) | POS_PG_DSN → DASHBOARD_PG_DSN 14 sections sync | Chạy khi startup hoặc POST /api/pos/sync |
| executive_dashboard/app/react_logic.py | Đọc từ Dashboard PG trả JSON cho API | get_conn() → SELECT → dict Không write data | 15+ payload functions |
| executive_dashboard/app/main.py | FastAPI app + lifecycle + sync endpoints | Import tất cả module khác Lifespan: init schema + sync | Port 8000 |
| executive_dashboard/app/wms_sync.py | Sync tồn kho từ WMS (rocky_wms_dev) | WMS_PG_DSN → DASHBOARD_PG_DSN | Inventory, StockTransfer |
| executive_dashboard/app/auth.py | JWT Auth + RBAC | Users table trong Dashboard PG | admin/changeme123 |
|  | FRONTEND (React) |  |  |
| executive_dashboard_frontend/ src/lib/api.ts | Gọi API backend (fetch wrapper) | /api/react/* endpoints | Token-based auth |
| executive_dashboard_frontend/ src/pages/*.tsx | Hiển thị data từ API (charts, tables) | Gọi api.ts → render | 9 pages |
|  | CONFIG |  |  |
| executive_dashboard/.env.pg | Env vars (không commit) | DASHBOARD_PG_DSN POS_PG_DSN WMS_PG_DSN | Gitignored |
| C:\rocky-dashboard\start_backend.bat | Script chạy trên server (set env + uvicorn) | Scheduled Task: rocky_backend | Auto-start on reboot |


# FILE: mcp_server_questions.xlsx

## SHEET: MCP Server Q&A (64 rows, 5 cols)

| # | Nhóm | Câu hỏi mẫu | Data Source (Bảng/Trường) | SQL Logic |
| --- | --- | --- | --- | --- |
|  | 1. DOANH THU & DOANH SỐ |  |  |  |
| 1 | Doanh thu | Doanh thu hôm nay/tuần này/tháng này bao nhiêu? | daily_sales.revenue | SELECT SUM(revenue) FROM daily_sales WHERE d BETWEEN {from} AND {to} |
| 2 | Doanh thu | Doanh thu cửa hàng X ngày Y | daily_sales.revenue + stores | SELECT revenue FROM daily_sales WHERE store_id = X AND d = Y |
| 3 | Doanh thu | So sánh doanh thu tháng này vs tháng trước | monthly_revenue | SELECT year_month, revenue, growth_pct FROM monthly_revenue |
| 4 | Doanh thu | Top 5 ngày doanh thu cao nhất | daily_sales | SELECT d, SUM(revenue) FROM daily_sales GROUP BY d ORDER BY 2 DESC LIMIT 5 |
| 5 | Doanh thu | Tại sao doanh thu hôm nay = 0? | POS: PaymentOrder.IssueAt | Check PaymentOrder WHERE IssueAt::date = today → không có phiếu thu hoàn tất |
| 6 | Doanh thu | Doanh thu theo từng cửa hàng | daily_sales + stores | SELECT s.name, SUM(ds.revenue) FROM daily_sales ds JOIN stores s GROUP BY s.name |
| 7 | Doanh số | Doanh số hôm nay bao nhiêu? | daily_sales.subtotal | SELECT SUM(subtotal) FROM daily_sales WHERE d = today |
| 8 | Doanh số | Tại sao doanh thu > doanh số? | daily_sales + POS | Vì thu nợ cũ (PaymentOrder.IssueAt cho đơn ApproveAt tháng trước) |
| 9 | Doanh số | Doanh số theo cửa hàng | daily_sales.subtotal + stores | SELECT s.name, SUM(ds.subtotal) FROM daily_sales ds JOIN stores s GROUP BY s.name |
|  | 2. NHÂN VIÊN |  |  |  |
| 10 | Nhân viên | Nhân viên nào bán nhiều nhất tháng này? | daily_staff_revenue + staff | SELECT s.name, SUM(sr.revenue) FROM daily_staff_revenue sr JOIN staff s ORDER BY 2 DESC LIMIT 10 |
| 11 | Nhân viên | Doanh thu nhân viên X từ ngày A đến B | daily_staff_revenue | SELECT d, revenue, orders_n FROM daily_staff_revenue WHERE staff_id = X AND d BETWEEN A AND B |
| 12 | Nhân viên | Bao nhiêu đơn không gán nhân viên? | POS: Order.StaffId | SELECT COUNT(*) FROM "Order" WHERE "StaffId" IS NULL AND "CompleteAt" IS NOT NULL |
| 13 | Nhân viên | Danh sách nhân viên đang hoạt động | staff | SELECT name, code, phone FROM staff |
| 14 | Nhân viên | So sánh performance giữa các nhân viên | daily_staff_revenue | SELECT staff_id, SUM(revenue), SUM(orders_n), COUNT(DISTINCT d) as active_days GROUP BY staff_id |
|  | 3. CÔNG NỢ B2B |  |  |  |
| 15 | Công nợ | Khách nào đang nợ nhiều nhất? | debt_report | SELECT customer_name, current_balance FROM debt_report ORDER BY current_balance ASC LIMIT 10 |
| 16 | Công nợ | Tổng công nợ hiện tại bao nhiêu? | debt_report | SELECT SUM(current_balance) FROM debt_report WHERE start_at = (SELECT MAX(start_at)...) |
| 17 | Công nợ | Khách X nợ bao nhiêu, trả được bao nhiêu? | debt_report | SELECT previous_balance, debt_amount, total_receive_amount, current_balance WHERE customer_name = X |
| 18 | Công nợ | Tỷ lệ thu hồi nợ tháng này? | debt_report.recover_debt_rate | SELECT AVG(recover_debt_rate) FROM debt_report WHERE start_at >= {month} |
| 19 | Công nợ | Khách nợ quá 2 tháng? | debt_report (aging) | Khách có current_balance < 0 liên tục > 60 ngày |
| 20 | Công nợ | Biến động công nợ tuần này vs tuần trước? | debt_report | Compare SUM(current_balance) between 2 periods |
|  | 4. ĐƠN HÀNG |  |  |  |
| 21 | Đơn hàng | Danh sách đơn hàng hôm nay | order_list | SELECT * FROM order_list WHERE LEFT(complete_at,10) = today |
| 22 | Đơn hàng | Đơn nào thanh toán bằng công nợ? | order_list.payment_method | SELECT * FROM order_list WHERE payment_method = 'Công nợ' |
| 23 | Đơn hàng | Có bao nhiêu đơn tặng (Type=3)? | POS: Order.Type | SELECT COUNT(*) FROM "Order" WHERE "Type" = 3 AND "DeleteAt" IS NULL |
| 24 | Đơn hàng | Đơn nào chưa hoàn thành? | POS: Order | SELECT * FROM "Order" WHERE "ApproveAt" IS NOT NULL AND "CompleteAt" IS NULL |
| 25 | Đơn hàng | Phương thức thanh toán phổ biến nhất? | payment_methods | SELECT method_name, SUM(amount) FROM payment_methods GROUP BY method_name ORDER BY 2 DESC |
|  | 5. TỒN KHO |  |  |  |
| 26 | Tồn kho | Tổng giá trị tồn kho hiện tại? | inventory_wms.inventory_value | SELECT SUM(inventory_value) FROM inventory_wms |
| 27 | Tồn kho | Sản phẩm nào hết hàng? | inventory_wms | SELECT product_name FROM inventory_wms WHERE on_hand <= 0 |
| 28 | Tồn kho | Hàng chết (dead stock) bao nhiêu SKU? | inventory_wms.is_dead_stock | SELECT COUNT(*) FROM inventory_wms WHERE is_dead_stock = 1 |
| 29 | Tồn kho | Tồn kho theo nhóm sản phẩm? | inventory_wms.category | SELECT category, SUM(on_hand), SUM(inventory_value) FROM inventory_wms GROUP BY category |
| 30 | Tồn kho | Stock cover days trung bình? | inventory_wms.stock_cover_days | SELECT AVG(stock_cover_days) FROM inventory_wms WHERE on_hand > 0 |
|  | 6. KHÁCH HÀNG |  |  |  |
| 31 | Khách hàng | Bao nhiêu khách mới tháng này? | daily_customer_segments | SELECT SUM(new_customers_n) FROM daily_customer_segments WHERE d BETWEEN {from} AND {to} |
| 32 | Khách hàng | Tỷ lệ khách quay lại? | daily_customer_segments | returning / (new + returning) * 100 |
| 33 | Khách hàng | Top 10 khách chi tiêu nhiều nhất? | customer_rfm | SELECT name, monetary, frequency FROM customer_rfm ORDER BY monetary DESC LIMIT 10 |
| 34 | Khách hàng | Phân khúc RFM: bao nhiêu Champion/Loyal/At-Risk? | customer_rfm.segment | SELECT segment, COUNT(*) FROM customer_rfm GROUP BY segment |
| 35 | Khách hàng | Khách nào sắp mất (At-Risk)? | customer_rfm | SELECT name, recency_days, monetary FROM customer_rfm WHERE segment = 'At-Risk' |
|  | 7. SẢN PHẨM |  |  |  |
| 36 | Sản phẩm | Sản phẩm bán chạy nhất tháng này? | product_performance | SELECT name, revenue, units_sold FROM product_performance WHERE year_month = {month} ORDER BY revenue DESC LIMIT 10 |
| 37 | Sản phẩm | Danh mục nào đóng góp nhiều nhất? | product_performance.category | SELECT category, SUM(revenue) FROM product_performance GROUP BY category ORDER BY 2 DESC |
| 38 | Sản phẩm | Sản phẩm nào bán ít nhất? | product_performance | ORDER BY units_sold ASC LIMIT 10 |
|  | 8. CỬA HÀNG |  |  |  |
| 39 | Cửa hàng | Cửa hàng nào doanh thu cao nhất? | daily_sales + stores | SELECT s.name, SUM(ds.revenue) JOIN stores ORDER BY 2 DESC |
| 40 | Cửa hàng | So sánh 3 cửa hàng | daily_sales + stores | Filter by store_ids, compare metrics |
| 41 | Cửa hàng | Tăng trưởng cửa hàng X so với tháng trước? | monthly_revenue.growth_pct | SELECT growth_pct FROM monthly_revenue WHERE store_id = X |
| 42 | Cửa hàng | Bảng xếp hạng cửa hàng | daily_sales + stores | Store leaderboard: revenue, orders, growth |
|  | 9. PHÂN TÍCH (Advanced) |  |  |  |
| 43 | Phân tích | Giải thích tại sao doanh thu > doanh số? | POS: PaymentOrder + Order | Cross-query: payments trong kỳ cho đơn ApproveAt trước kỳ (thu nợ cũ) |
| 44 | Phân tích | Bao nhiêu tiền thu nợ cũ trong tháng? | POS: PaymentOrderItem + Order | WHERE IssueAt in month AND Order.ApproveAt < month_start |
| 45 | Phân tích | Trend doanh thu 6 tháng gần nhất? | monthly_revenue | SELECT year_month, revenue ORDER BY year_month DESC LIMIT 6 |
| 46 | Phân tích | GPM (biên lợi nhuận gộp) hiện tại? | daily_sales: revenue, cogs | (SUM(revenue) - SUM(cogs)) / SUM(revenue) * 100 |
| 47 | Phân tích | Tỷ lệ trả hàng tháng này? | monthly_returns | return_count / order_count * 100 |
| 48 | Phân tích | AOV (giá trị đơn trung bình)? | daily_sales | SUM(revenue) / SUM(orders_n) |
|  | 10. KHÔNG TRẢ LỜI ĐƯỢC |  |  |  |
| 49 | N/A | CSAT (hài lòng khách hàng) thật? | Cần ZNS database | Chưa kết nối ZNS_PG_DSN |
| 50 | N/A | Target doanh thu tháng này? | Chưa có data target | Cần nhập thủ công |
| 51 | N/A | Hoa hồng nhân viên? | POS: Commission (chưa implement) | Cần implement sync Commission |
| 52 | N/A | Số khách walk-in hôm nay? | Không có sensor | Cần thiết bị đếm người |
| 53 | N/A | Chi phí vận hành (OPEX) thực tế? | Không có data | Hiện dùng proxy 12% |

