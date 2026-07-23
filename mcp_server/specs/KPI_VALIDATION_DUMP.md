
# FILE: cau_hoi_nghiep_vu_cho_leader.xlsx

## SHEET: 1. Bán hàng (Sales) (9 rows, 4 cols)

| STT | Câu hỏi | Lý do cần hỏi | Ghi chú (Leader trả lời) |
| --- | --- | --- | --- |
| 1 | Quy trình đơn hàng từ lúc khách vào đến khi thanh toán xong gồm những bước nào? (Walk-in → Khám mắt → Chọn gọng → Đo kính → Thanh toán → Giao kính) | Hiện tại dùng proxy orders*1.6 cho walk-in vì không có data thật |  |
| 2 | Khi nào đơn được tính là "hoàn thành" — ApproveAt hay CompleteAt? Trường hợp nào đơn Approve rồi nhưng không Complete? | Liên quan doanh số vs doanh thu. Hiện có 425 đơn Approve nhưng chưa Complete |  |
| 3 | Đơn hàng có bao nhiêu loại? (bán lẻ, bán buôn B2B, bán online, trả góp, khuyến mại...) Phân biệt bằng trường nào? | Cần filter đúng loại đơn cho từng metric |  |
| 4 | Phí ship (ShippingFee) tính vào doanh thu hay không? Trường ApproveAt và CompleteAt của ShippingFee nghĩa gì? | Leader đã mention trước đó nhưng chưa rõ logic |  |
| 5 | PaymentOrder.DocumentType có những giá trị nào? (1=Phiếu thu, còn gì nữa?) | Hiện chỉ filter DocumentType=1, cần biết các loại khác |  |
| 6 | Đơn hủy (CancelAt) có cần tính vào báo cáo không? Khi nào đơn bị hủy? | Để loại bỏ đơn hủy khỏi thống kê chính xác |  |
| 7 | Một đơn hàng có thể có nhiều PaymentOrder không? (trả nhiều lần, trả góp) | Ảnh hưởng đến cách tính doanh thu theo ngày |  |
| 8 | Voucher/Chiết khấu năm giảm doanh thu hay ghi nhận riêng? Trường nào trong POS? | PaymentMethod có "Chiết khấu năm" và "Voucher khách hàng" — cần biết cách xử lý |  |


## SHEET: 2. Công nợ B2B (Debt) (9 rows, 4 cols)

| STT | Câu hỏi | Lý do cần hỏi | Ghi chú (Leader trả lời) |
| --- | --- | --- | --- |
| 1 | Khách B2B (đại lý) khác khách lẻ bằng trường nào? Có trường CustomerType hay phải dùng CustomerGroup? | Cần tách dashboard B2C vs B2B |  |
| 2 | DebtReport.PreviousBalance âm (-135,000) nghĩa là khách nợ hay cửa hàng nợ khách? | Data thực tế thấy giá trị âm, cần hiểu chiều nợ |  |
| 3 | Chu kỳ báo cáo công nợ là gì? (daily? weekly? monthly?) Leader muốn xem theo kỳ nào? | DebtReport có StartAt/EndAt daily, nhưng leader có thể muốn xem theo tháng |  |
| 4 | Tỷ lệ thu hồi nợ (RecoverDebtRate) tính thế nào? Mục tiêu thu hồi bao nhiêu %? | Cần biết KPI target để hiển cảnh báo |  |
| 5 | Khách nợ quá hạn bao nhiêu ngày thì cảnh báo? Có mức độ (xanh/vàng/đỏ)? | Để làm alert trên dashboard |  |
| 6 | Công nợ có phân biệt theo loại (công nợ hàng hóa vs công nợ dịch vụ)? | Báo cáo công nợ cần tách loại hay gộp? |  |
| 7 | Ai là người duyệt thanh toán công nợ? Quy trình thu nợ như thế nào? | Hiểu workflow để thiết kế dashboard phù hợp |  |
| 8 | Có tính lãi/phạt cho nợ quá hạn không? | Cần biết có trường nào trong DB lưu lãi/phạt |  |


## SHEET: 3. Nhân sự (Staff) (9 rows, 4 cols)

| STT | Câu hỏi | Lý do cần hỏi | Ghi chú (Leader trả lời) |
| --- | --- | --- | --- |
| 1 | Mỗi cửa hàng có bao nhiêu nhân viên? Số liệu lấy từ đâu (bảng Staff)? Có nhân viên part-time không? | Hiện default = 12, cần số thật cho Revenue/Staff |  |
| 2 | Hoa hồng (commission) tính theo doanh thu hay doanh số? Công thức? | POS có bảng Commission nhưng chưa dùng |  |
| 3 | KPI cho nhân viên bán hàng là gì? (doanh thu/ngày, số đơn/ngày, tỷ lệ chốt?) | Để hiển thị performance scoring |  |
| 4 | Nhân viên làm việc theo ca như thế nào? (full-time, part-time, ca sáng/chiều) | Ảnh hưởng cách tính productivity/hour |  |
| 5 | Có đánh giá nhân viên hàng tháng không? Tiêu chí nào? | Để làm bảng xếp hạng nhân viên |  |
| 6 | StaffId trong Order là người bán hay người tạo đơn? Có nhiều người phục vụ 1 đơn không? | Hiện quy hết doanh thu cho 1 StaffId, có thể sai |  |
| 7 | Nhân viên mới vào bao lâu thì được tính KPI? Có thời gian thử việc? | Để loại nhân viên mới khỏi bảng xếp hạng |  |
| 8 | Target doanh thu cho từng nhân viên là bao nhiêu? Ai đặt? | Cần data target để tính % đạt chỉ tiêu |  |


## SHEET: 4. Tồn kho (Inventory) (9 rows, 4 cols)

| STT | Câu hỏi | Lý do cần hỏi | Ghi chú (Leader trả lời) |
| --- | --- | --- | --- |
| 1 | Sản phẩm gọng kính, tròng kính, phụ kiện — phân loại bằng ProductCategory hay trường khác? | Cần hiển inventory theo nhóm đúng |  |
| 2 | Dead stock (hàng chết) định nghĩa thế nào? Bao nhiêu ngày không bán là dead stock? (30? 60? 90?) | Hiện dùng 90 ngày nhưng chưa confirm |  |
| 3 | Khi nào thì cần đặt hàng thêm? Có mức tồn kho tối thiểu (reorder point) cho từng SKU không? | Để làm alert khi sắp hết hàng |  |
| 4 | Luân chuyển hàng giữa các cửa hàng (transfer) có phổ biến không? Logic nào? | WMS có InventoryHistory nhưng chưa phân biệt transfer vs sale |  |
| 5 | Hàng tồn kho tính theo giá vốn (CostPrice) hay giá bán? Giá vốn cập nhật bao lâu 1 lần? | Ảnh hưởng tính Inventory Value và GMROI |  |
| 6 | Có sản phẩm nào theo mùa (seasonal)? Ví dụ gọng mắt trời chỉ bán hè? | Để phân tích xu hướng tồn kho theo mùa |  |
| 7 | Sản phẩm lỗi/hư tính vào tồn kho hay tách riêng? | Cần biết có trạng thái sản phẩm (tốt/hư/bảo hành) |  |
| 8 | Warehouse trong WMS và Warehouse trong POS có map 1-1 không? | Hiện dùng WarehouseId để map store, cần xác nhận |  |


## SHEET: 5. Khách hàng (Customer) (10 rows, 4 cols)

| STT | Câu hỏi | Lý do cần hỏi | Ghi chú (Leader trả lời) |
| --- | --- | --- | --- |
| 1 | Khách "quay lại" (returning) định nghĩa thế nào? Mua lần 2 trong bao lâu? (30 ngày? 6 tháng? 1 năm?) | Kính mắt là sản phẩm mua ít lần/năm |  |
| 2 | Có chạy campaign marketing nào trên POS không? (voucher, khuyến mại, giảm giá theo mùa) | Bảng Campaign/Promotion trong POS chưa dùng |  |
| 3 | Target doanh thu hàng tháng của mỗi cửa hàng là bao nhiêu? Ai nhập? | Hiện không có data target, cần cho phần "% đạt target" |  |
| 4 | Khách VIP/thân thiết phân loại thế nào? Có chương trình loyalty/tích điểm? | Để làm phân khúc khách hàng chính xác hơn |  |
| 5 | CSAT (hài lòng khách hàng) đo bằng cách nào? Zalo survey? Google review? Trực tiếp tại cửa hàng? | Hiện chỉ có proxy từ tỷ lệ trả hàng |  |
| 6 | Khách mua kính trung bình bao lâu mua lại? (1 năm? 2 năm?) | Để tính Customer Lifetime Value đúng |  |
| 7 | Có phân biệt khách online vs offline? Kênh bán hàng nào quan trọng nhất? | Để làm báo cáo channel mix |  |
| 8 | Remake (làm lại kính) xảy ra khi nào? Do sai số đo hay khách đổi ý? Tỉ lệ chấp nhận? | Hiện dùng proxy MeasurementTicket trong 14 ngày, chưa chính xác |  |
| 9 | Có thu thập số điện thoại/email khách để remarketing không? Tỉ lệ có thông tin? | Ảnh hưởng khả năng làm retention campaign |  |


# FILE: hieu_biet_nghiep_vu_validate_sau_sửa.xlsx

## SHEET: 1. Doanh thu & Doanh số (23 rows, 6 cols)

| Khái niệm | Mô tả nghiệp vụ | Công thức / Logic | Bảng & Trường trong DB | Ví dụ (80K hàng + 20K ship, trả 60K) | Đúng/Sai |
| --- | --- | --- | --- | --- | --- |
| --- QUY TRÌNH ĐƠN HÀNG --- |  |  |  |  |  |
| Bước 1: Chọn SP | Khách chọn sản phẩm trên App/POS | Tạo OrderItem với Quantity, Price | OrderItem.ProductId, OrderItem.Quantity, OrderItem.Price | Chọn gọng kính 80K |  |
| Bước 2: Checkout | Xác nhận đơn, tính tổng | TotalAmount = ProductAmount + ShipFee - Discount | Order.TotalAmount, Order.ShippingFee, Order.DiscountAmount, Order.ProductAmount | Total = 80K + 20K = 100K |  |
| Bước 3: Thanh toán | Khách trả tiền (toàn bộ hoặc 1 phần) | Tạo PaymentOrder + PaymentOrderItem với PaidAmount | PaymentOrderItem.PaidAmount, PaymentOrder.DocumentType=1 (Phiếu thu) | Trả 60K → PaymentOrderItem.PaidAmount = 60,000 |  |
| Bước 4: Duyệt xuất hàng | Đơn được duyệt → ApproveAt được set | Order.ApproveAt = NOW() | Order.ApproveAt (NOT NULL = đơn hợp lệ) | ApproveAt = 2026-06-01 16:09 |  |
| Bước 5: Hoàn thành | Đơn giao xong → CompleteAt được set | Order.CompleteAt = NOW() | Order.CompleteAt (NOT NULL = đã giao) | CompleteAt = 2026-06-01 16:29 |  |
| --- DOANH SỐ (Subtotal) --- |  |  |  |  |  |
| Doanh số | Giá trị hàng hóa thuần (không ship, không phí khác) | SUM(OrderItem.SubTotalIncludeDiscount) WHERE Order.ApproveAt IS NOT NULL | OrderItem.SubTotalIncludeDiscount (qua OrderItemGroup → Order) | 80,000 (đúng = chỉ tiền hàng) |  |
| Không bao gồm | Phí ship, Voucher, Chiết khấu năm | ShippingFee KHÔNG tính vào doanh số | Order.ShippingFee (loại ra) | Ship 20K không tính |  |
| Group by ngày | Tính doanh số theo ngày duyệt đơn | GROUP BY Order.ApproveAt::date | Order.ApproveAt AT TIME ZONE Asia/Ho_Chi_Minh | Ngày 01/06/2026 |  |
| --- DOANH THU (Revenue) --- |  |  |  |  |  |
| Doanh thu | Tiền THỰC NHẬN từ khách (bao gồm cả ship nếu khách trả) | SUM(PaymentOrderItem.PaidAmount) WHERE PaymentOrder.CompleteAt IS NOT NULL   AND PaymentOrder.CancelAt IS NULL   AND PaymentOrder.DocumentType = 1   AND PaidAmount > 0 | PaymentOrderItem.PaidAmount PaymentOrder.CompleteAt PaymentOrder.DocumentType = 1 | 60,000 (chỉ phần đã trả) |  |
| Bao gồm Ship? | CÓ — nếu khách trả ship thì PaidAmount có cả ship | PaymentOrderItem.PaidAmount = số tiền khách thực chuyển | Data thật: Order.Total=165K, Ship=30K → PaidAmount=165K (bao gồm ship) | Nếu khách trả cả ship: 60K có thể gồm ship |  |
| Group by ngày | Tính doanh thu theo ngày phát hành phiếu thu | GROUP BY PaymentOrder.IssueAt::date | PaymentOrder.IssueAt AT TIME ZONE Asia/Ho_Chi_Minh | Ngày 01/06/2026 |  |
| --- PHÍ SHIP --- |  |  |  |  |  |
| Phí ship | Phí vận chuyển đơn hàng | Nằm trong Order.TotalAmount nhưng KHÔNG tính vào doanh số | Order.ShippingFee | 20,000 |  |
| Không tính vào | Doanh số, Tồn kho, SELL (units), ROS | Leader xác nhận: Tồn kho=KHÔNG, SELL=KHÔNG, ROS=KHÔNG | Chỉ là phụ phí, không phải sản phẩm | Ship 20K loại khỏi tất cả metric trừ doanh thu |  |
| Có tính vào | Doanh thu (nếu khách trả ship) | PaymentOrderItem.PaidAmount bao gồm cả ship fee | Khách trả bao nhiêu thì PaidAmount bấy nhiêu | Nếu khách trả 100K (gồm 20K ship) → Revenue = 100K |  |
| --- CÔNG NỢ --- |  |  |  |  |  |
| Công nợ phát sinh | Phần khách chưa trả của đơn hàng | Order.NeedPayAmount - Order.PaidAmount = Order.LeftAmount | Order.LeftAmount | 100K - 60K = 40K còn nợ |  |
| DebtReport ghi nhận | Snapshot công nợ hàng ngày per customer | DebtAmount = tổng nợ phát sinh mới trong kỳ TotalReceiveAmount = tổng đã thu trong kỳ | DebtReport.DebtAmount DebtReport.TotalReceiveAmount DebtReport.PaidAmount | DebtAmount=40K (nợ mới) TotalReceiveAmount=60K (đã thu) |  |
| CurrentBalance | Số dư nợ cuối kỳ (âm = khách nợ) | CurrentBalance = PreviousBalance + DebtAmount - TotalReceiveAmount (hoặc PreviousBalance - net change) | DebtReport.CurrentBalance DebtReport.PreviousBalance | Prev=0, Debt=40K, Recv=60K → Current = 0 + 40K - 60K = -20K?? (cần validate logic chính xác) |  |


## SHEET: 2. Loại đơn & DocumentType (20 rows, 6 cols)

| Trường | Giá trị | Ý nghĩa | Bảng trong DB | Ảnh hưởng đến metric | Đúng/Sai |
| --- | --- | --- | --- | --- | --- |
| --- ORDER TYPE --- |  |  |  |  |  |
| Order.Type | 1 | Bán thường (tại cửa hàng) | "Order"."Type" = 1 | Tính vào doanh số + doanh thu |  |
| Order.Type | 2 | Bán đơn dây | "Order"."Type" = 2 | Tính vào doanh số + doanh thu |  |
| Order.Type | 3 | Đơn tặng (không thu tiền?) | "Order"."Type" = 3 | Không tính doanh thu? Cần confirm |  |
| Order.Type | 4 | (Chưa rõ — leader ghi #4) | "Order"."Type" | Cần clarify |  |
| --- DOCUMENT TYPE --- |  |  |  |  |  |
| PaymentOrder.DocumentType | 1 | Phiếu thu (Receive) — tiền VÀO | "PaymentOrder"."DocumentType" | Tính vào Doanh thu (SUM PaidAmount) |  |
| PaymentOrder.DocumentType | 2 | Phiếu chi (Payment) — tiền RA | "PaymentOrder"."DocumentType" | KHÔNG tính vào doanh thu. Dùng cho hoàn tiền/chi phí |  |
| --- ĐIỀU KIỆN TÍNH DOANH THU --- |  |  |  |  |  |
| PaymentOrder.CompleteAt | NOT NULL | Phiếu thu đã hoàn tất | "PaymentOrder"."CompleteAt" | Bắt buộc để tính doanh thu |  |
| PaymentOrder.CancelAt | IS NULL | Phiếu thu chưa bị hủy | "PaymentOrder"."CancelAt" | Loại phiếu đã hủy |  |
| PaymentOrderItem.PaidAmount | > 0 | Có số tiền thực nhận | "PaymentOrderItem"."PaidAmount" | Loại dòng PaidAmount = 0 |  |
| Order.ApproveAt | NOT NULL | Đơn đã duyệt xuất hàng | "Order"."ApproveAt" | Điều kiện cho doanh số (và có thể doanh thu) |  |
| --- PAYMENT METHOD --- |  |  |  |  |  |
| PaymentMethod.Name | Chuyển khoản | Thanh toán CK cá nhân/công ty | "PaymentMethod"."Name" | Phân loại PTTT |  |
| PaymentMethod.Name | Công nợ | Ghi nợ (B2B) | "PaymentMethod"."Name" | Đơn công nợ → DebtReport |  |
| PaymentMethod.Name | Chiết khấu năm | Giảm giá cho đại lý | "PaymentMethod"."Name" | Giảm PaidAmount thực nhận |  |
| PaymentMethod.Name | Voucher KH | Voucher khuyến mại | "PaymentMethod"."Name" | Giảm PaidAmount thực nhận |  |
| PaymentMethod.Name | Ví chính/Ví xu | Ví điện tử nội bộ | "PaymentMethod"."Name" | Tính vào doanh thu như tiền mặt |  |


## SHEET: 3. Công nợ B2B (17 rows, 6 cols)

| Khái niệm | Mô tả | Trường trong DB | Ví dụ (80K hàng, 20K ship, trả 60K) | Ghi chú | Đúng/Sai |
| --- | --- | --- | --- | --- | --- |
| --- KHÁCH B2B --- |  |  |  |  |  |
| Phân biệt khách B2B | Customer.Type = 1 là đại lý (B2B) | "Customer"."Type" = 1 | Filter: WHERE Customer.Type = 1 | Type=2 là khách lẻ |  |
| --- DEBT REPORT (Snapshot hàng ngày) --- |  |  |  |  |  |
| PreviousBalance | Số dư nợ đầu kỳ (âm = Rocky nợ) | "DebtReport"."PreviousBalance" | Ngày 01/06: PreviousBalance = -40,000 (nợ cũ từ hôm trước) | Âm = Rocky nợ khách hàng |  |
| DebtAmount | Nợ phát sinh MỚI trong kỳ (từ đơn mới) | "DebtReport"."DebtAmount" | Đơn mới 100K, trả 60K → nợ mới = 40,000 | Chỉ tính phần chưa thu của đơn mới |  |
| TotalReceiveAmount | Tổng tiền ĐÃ THU ĐƯỢC trong kỳ | "DebtReport"."TotalReceiveAmount" | Thu 60K từ đơn mới → TotalReceiveAmount = 60,000 | Gồm thanh toán đơn mới + thu nợ cũ |  |
| TotalPaymentAmount | Tổng tiền đã CHI RA trong kỳ (hoàn tiền) | "DebtReport"."TotalPaymentAmount" | Không hoàn tiền → 0 | DocumentType=2 (Phiếu chi) |  |
| PaidAmount | Số tiền khách đã thanh toán trong kỳ | "DebtReport"."PaidAmount" | Khách trả 60K → PaidAmount = 60,000 | TotalReceiveAmount - TotalPaymentAmount |  |
| CurrentBalance | Số dư nợ cuối kỳ | "DebtReport"."CurrentBalance" | Prev(-40K) + Debt(40K) - Receive(60K) = -60K? Hoặc: Prev(-40K) - Debt(40K) = -80K + Recv(60K) = -20K? | Cần validate công thức chính xác |  |
| RecoverDebtRate | Tỷ lệ thu hồi nợ trong kỳ | "DebtReport"."RecoverDebtRate" | Thu 60K / Tổng nợ cần thu? = ??% | Công thức chưa rõ |  |
| StartAt / EndAt | Khoảng thời gian của snapshot (1 ngày) | "DebtReport"."StartAt", "EndAt" | StartAt=2026-06-01 00:00, EndAt=2026-06-01 23:59 | Mỗi ngày 1 record per customer |  |
| --- AGING BUCKETS (Tuổi nợ) --- |  |  |  |  |  |
| 1 tháng (1M) | Nợ từ 0-30 ngày | Tính từ: NOW() - Order.ApproveAt <= 30 days | Khách nợ 40K trong 5 ngày → bucket 1M | Mức thấp, chưa cảnh báo |  |
| 2 tháng (2M) | Nợ từ 31-60 ngày | NOW() - Order.ApproveAt BETWEEN 31 AND 60 | Nợ 40K quá 40 ngày → bucket 2M | Cảnh báo vàng? |  |
| 3 tháng (3M) | Nợ từ 61-90 ngày | NOW() - Order.ApproveAt BETWEEN 61 AND 90 |  | Cảnh báo cam |  |
| 4 tháng (4M) | Nợ trên 90 ngày | NOW() - Order.ApproveAt > 90 |  | Cảnh báo đỏ — nợ xấu |  |


## SHEET: 4. Nhân sự & Tồn kho & KH (13 rows, 5 cols)

| Chủ đề | Hiểu biết của tôi | Trường trong DB | Logic / Ghi chú | Đúng/Sai |
| --- | --- | --- | --- | --- |
| --- NHÂN SỰ --- |  |  |  |  |
| StaffId nullable | Một đơn hàng có thể không gán nhân viên (StaffId = NULL) | "Order"."StaffId" (nullable) | Khi StaffId NULL → không tính vào doanh thu per staff |  |
| Staff revenue | Doanh thu per staff = SUM PaymentOrderItem.PaidAmount theo StaffId | COALESCE(Order.StaffId, PaymentOrder.StaffId) | Fallback: nếu Order không có StaffId thì lấy từ PaymentOrder |  |
| --- TỒN KHO --- |  |  |  |  |
| Product Type | Phân loại: Gọng kính, Tròng kính, Phụ kiện | "Product"."Type" hoặc ProductCategory | Cần xác nhận trường chính xác |  |
| StockTransfer | Luân chuyển hàng giữa cửa hàng nằm trong WMS | WMS database (rocky_wms_dev): bảng StockTransfer | Không nằm trong POS database |  |
| Dead stock | Hàng chết = không bán được trong 90 ngày | Tính từ InventoryHistory.IssueAt (WMS) | Nếu last movement > 90 ngày = dead stock |  |
| Inventory value | Tính theo giá vốn (CostPrice) | "ProductItemWarehouseInventory"."CostPrice" * "StockQuantity" (WMS) | Không dùng giá bán |  |
| --- KHÁCH HÀNG --- |  |  |  |  |
| MemberShipLevel | Phân hạng khách VIP/Loyalty | Bảng "MemberShipLevel" trong POS (?) | Dùng để phân khúc khách hàng |  |
| SĐT khách hàng | 99% khách đã có số điện thoại | "Customer"."Phone" | Có thể dùng cho remarketing/retention |  |
| Khách quay lại | Định nghĩa: mua lần 2+ (không có mốc thời gian cụ thể) | COUNT(DISTINCT Order per Customer) >= 2 where betweeen | Kính mắt: chu kỳ mua lại dài (1-2 năm) |  |


## SHEET: 5. SQL Formulas (7 rows, 5 cols)

| Metric | SQL Logic | Trường chính | Filter | Đúng/Sai |
| --- | --- | --- | --- | --- |
| Doanh số (Subtotal) | SELECT SUM(oi."SubTotalIncludeDiscount") FROM "OrderItem" oi JOIN "OrderItemGroup" oig ON oig."Id" = oi."OrderItemGroupId" JOIN "Order" o ON o."Id" = oig."OrderId" WHERE o."ApproveAt" IS NOT NULL   AND o."DeleteAt" IS NULL   AND oi."DeleteAt" IS NULL | OrderItem.SubTotalIncludeDiscount | Order.ApproveAt IS NOT NULL DeleteAt IS NULL |  |
| Doanh thu (Revenue) | SELECT SUM(poi."PaidAmount") FROM "PaymentOrderItem" poi JOIN "PaymentOrder" po ON po."Id" = poi."PaymentOrderId" WHERE po."CompleteAt" IS NOT NULL   AND po."CancelAt" IS NULL   AND po."DocumentType" = 1   AND poi."PaidAmount" > 0   AND po."DeleteAt" IS NULL | PaymentOrderItem.PaidAmount | PaymentOrder: CompleteAt NOT NULL CancelAt IS NULL DocumentType = 1 PaidAmount > 0 |  |
| Số lượng bán | SELECT SUM(oi."Quantity") FROM "OrderItem" oi JOIN "OrderItemGroup" oig ... JOIN "Order" o ... WHERE o."CompleteAt" IS NOT NULL | OrderItem.Quantity | Order.ApproveAt IS NOT NULL |  |
| Công nợ khách B2B | SELECT * FROM "DebtReport" WHERE "DeleteAt" IS NULL   AND "CustomerId" IN (SELECT "Id" FROM "Customer" WHERE "Type" = 1) | DebtReport.* | Customer.Type = 1 (B2B) DeleteAt IS NULL |  |
| Doanh thu per Staff | SELECT COALESCE(o."StaffId") as staff_id,   SUM(poi."PaidAmount") FROM "PaymentOrderItem" poi JOIN "PaymentOrder" po ... LEFT JOIN "Order" o ... WHERE ... IS NOT NULL GROUP BY staff_id | Order.StaffId | COALESCE(Order.StaffId) IS NOT NULL |  |
| Tồn kho | SELECT i."ProductItemId", i."StockQuantity", i."CostPrice" FROM "ProductItemWarehouseInventory" i (WMS) WHERE i."DeleteAt" IS NULL | ProductItemWarehouseInventory.StockQuantity (WMS) | WMS database: rocky_wms_dev |  |


# FILE: KPI_VALIDATION_FOR_LEADER.xlsx

## SHEET: KPI Master List (41 rows, 12 cols)

| STT | Domain | KPI Name (EN) | KPI Name (VI) | Cong thuc | Bang POS Nguon | Cot POS Nguon | Bang Gold/SQLite | Grain | Don vi | Ghi chu / Logic dac biet | Leader Validate (OK/Sai/Can bo sung) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Finance | Total Revenue | Tong doanh thu | SUM(revenue_net) trong ky [start, end] | SaleOrder | NeedPayAmount, CompleteAt, SiteId, DeleteAt | daily_sales_finance | store x day | VND | Filter: CompleteAt IS NOT NULL AND DeleteAt IS NULL. Timezone convert truoc cat ngay. |  |
| 2 | Finance | Gross Profit Margin (GPM) | Bien loi nhuan gop | SUM(revenue_net - cogs_amount) / SUM(revenue_net) x 100 | SaleOrder + SaleOrderItem | SaleOrder.NeedPayAmount, SaleOrderItem.SubTotalCostPrice | daily_sales_finance | store x day | % | cogs_amount = SUM(SubTotalCostPrice) theo SaleOrder. COGS co the NULL. |  |
| 3 | Finance | Net Profit Margin (PROXY) | Bien LN rong (proxy) | (revenue - cogs - revenue x 0.12) / revenue x 100 | SaleOrder + SaleOrderItem | Nhu GPM + ENV: EDP_OPEX_PROXY_PCT (default 12%) | daily_sales_finance | store x day | % | OPEX la proxy co dinh 12%. KHONG phai NPM that. |  |
| 4 | Finance | ATV | Gia tri giao dich TB | SUM(revenue_net) / COUNT(DISTINCT orders) | SaleOrder | NeedPayAmount, Id | daily_sales_finance | store x day | VND | orders_n = COUNT don CompleteAt NOT NULL |  |
| 5 | Finance | Revenue per Staff | Doanh thu / nhan vien | SUM(revenue_net) / SUM(staff_count) | SaleOrder + Site | NeedPayAmount; staff_count tu stores | daily_sales_finance + stores | store x period | VND | staff_count mac dinh=12. La DT CA KY, khong phai per ngay. |  |
| 6 | Finance | Revenue Growth % | Tang truong DT | (rev_curr - rev_prev) / rev_prev x 100 | SaleOrder | NeedPayAmount | daily_sales_finance | store x month | % | So sanh ky truoc cung do dai |  |
| 7 | Customer | Churn Rate (PROXY) | Ty le mat khach (proxy) | (1 - repeat_rate) x 100 | SaleOrder | CustomerId, CompleteAt | daily_store_signals | store x day | % | PROXY: ty le don KHONG lap lai. Khong phai CRM churn. |  |
| 8 | Customer | UPT | San pham / don | SUM(Quantity) / COUNT(DISTINCT SaleOrder.Id) | SaleOrder + SaleOrderItem | SaleOrderItem.Quantity, SaleOrder.Id | daily_sales_finance | store x day | units | units_sold = SUM(Quantity) items trong don hoan tat |  |
| 9 | Customer | Remake Rate | Ty le lam lai kinh | SUM(remake_orders_n) / SUM(orders_n) x 100 | SaleOrder + MeasurementTicket | CustomerId/SiteId/CompleteAt + IssueAt | daily_sales_finance | store x day | % | PROXY: MeasurementTicket cung CustomerID+SiteId +-14d. Can verify cot IsRemake. |  |
| 10 | Customer | New Customers | Khach moi | COUNT(CustomerId lan dau mua) | SaleOrder | CustomerId, CompleteAt | daily_customer_segments | store x day | nguoi | Khong co CompleteAt truoc ky |  |
| 11 | Customer | Returning Customers | Khach quay lai | COUNT(CustomerId da mua truoc) | SaleOrder | CustomerId, CompleteAt | daily_customer_segments | store x day | nguoi | Co it nhat 1 don truoc ky |  |
| 12 | Customer | Retention Rate | Ty le giu chan | retained / customers_prev x 100 | SaleOrder | CustomerId, CompleteAt | monthly_customer_retention | store x month | % | Set-diff: KH co don ca M-1 va M / KH M-1 |  |
| 13 | Customer | CLV (Average) | Gia tri vong doi KH | SUM(revenue) / COUNT(DISTINCT customers) | SaleOrder | NeedPayAmount, CustomerId | customer_rfm_snapshot | customer | VND | Tong DT / tong KH unique |  |
| 14 | Customer/RFM | RFM - Champion | KH trung thanh nhat | recency<=30d AND frequency>=3 | SaleOrder | CustomerId, CompleteAt, Id, NeedPayAmount | customer_rfm_snapshot | customer | segment | recency=NOW()-MAX(CompleteAt), freq=COUNT(Id), monetary=SUM(NeedPayAmount) |  |
| 15 | Customer/RFM | RFM - Loyal | KH trung thanh | recency<=60d AND frequency>=2 | SaleOrder | Nhu tren | customer_rfm_snapshot | customer | segment |  |  |
| 16 | Customer/RFM | RFM - At-Risk | KH co rui ro | recency<=120d | SaleOrder | Nhu tren | customer_rfm_snapshot | customer | segment |  |  |
| 17 | Customer/RFM | RFM - Hibernating | KH ngu dong | recency<=365d | SaleOrder | Nhu tren | customer_rfm_snapshot | customer | segment |  |  |
| 18 | Customer/RFM | RFM - Lost | KH da mat | recency>365d | SaleOrder | Nhu tren | customer_rfm_snapshot | customer | segment |  |  |
| 19 | Inventory | Dead Stock % | Ty le ton chet | COUNT(qty<=0 OR is_return)/COUNT(*) x 100 | StockHistory + Warehouse | Quantity, IsReturn, WarehouseId; Warehouse.SiteId | monthly_inventory | store x month | % | PROXY tu StockHistory. Can review logic. |  |
| 20 | Inventory | Dead Stock SKU | SKU ton chet | sold_units=0 AND age_days>=threshold(90d) | StockItem + SaleOrderItem | InboundAt, Quantity(sold check) | monthly_inventory_sku | store x month x product | count | age_days=NOW()-InboundAt. Threshold: 30/60/90/180d. |  |
| 21 | Inventory | Stock Cover Days | Ngay ton bao phu | AVG(EndStock)/AVG(ABS(Quantity)) cap 3650 | StockHistory + Warehouse | EndStock, Quantity | monthly_inventory | store x month | days | NULLIF de tranh chia 0. Cap 3650. |  |
| 22 | Inventory | GMROI | Loi nhuan / Von ton | SUM(gross_profit)/SUM(inventory_value) | SaleOrderItem + StockItem | SubTotalCostPrice, CostPrice x stock | monthly_gmroi_category | category x month | ratio | Can monthly_inventory_sku xong truoc. |  |
| 23 | Inventory | OOS % | Ty le het hang | COUNT(stock<=0 AND sold>0)/COUNT(*) x 100 | StockItem + SaleOrderItem | stock qty, sold qty | monthly_inventory_sku | store x month x product | % | SKU tung ban nhung het hang |  |
| 24 | Inventory | STR % | Ty le ban het | SUM(sold)/(sold+stock) x 100 | StockItem + SaleOrderItem | sold + stock | monthly_inventory_sku | store x month | % |  |  |
| 25 | Inventory | Inventory Turnover | Vong quay hang ton | COGS / AVG(inventory_value) | SaleOrderItem + StockHistory | SubTotalCostPrice, EndStock x CostPrice | monthly_inventory_sku | store x month | turns |  |  |
| 26 | Inventory | Inventory Ageing | Tuoi ton kho | <30d / 31-90d / 91-180d / >180d | StockItem | InboundAt | monthly_inventory_ageing | store x month x bucket | count | 4 buckets. age_days=NOW()-InboundAt. |  |
| 27 | Quality | CSAT (Real) | Diem hai long (that) | AVG(Score) x 20 (0-100) | ZnsDb: Rating | Score, CreatedAt, SiteId | monthly_csat | store x month | score | Chi khi ZNS_PG_DSN co. |  |
| 28 | Quality | CSAT (PROXY) | Diem hai long (proxy) | 5 - defect_rate x 8 (1-5) | ReturnSaleOrder + SupplierWarranty | return+warranty count / orders | monthly_quality_returns | store x month | score 1-5 | Fallback khi khong co ZNS. |  |
| 29 | Quality | Return Rate % | Ty le doi tra | (returns+warranties)/orders x 100 | ReturnSaleOrder + SupplierWarranty + SaleOrder | Counts of each | monthly_quality_returns | store x month | % | Filter: DeleteAt IS NULL |  |
| 30 | Quality | Cohort Retention | Giu chan cohort | base x decay[1.0,0.62,0.42,0.31,0.24,0.18] | SaleOrder | CustomerId, CompleteAt | monthly_cohort_retention | cohort x month | % | Decay la PROXY. Can data that. |  |
| 31 | Marketing | Conversion Rate | Ty le chuyen doi | orders / measurement_tickets x 100 | SaleOrder + MeasurementTicket | CompleteAt count, IssueAt count | daily_measurement_funnel | store x day | % | MeasurementTicket co the rong o mot so store. |  |
| 32 | Marketing | Channel Mix % | Ty trong kenh | channel_rev / total_rev x 100 | SaleOrder + SaleChannel + EcomSource | SaleChannelId, Name, ShopName | daily_channel_sales | store x day x channel | % | Fallback='Offline/POS' khi NULL. |  |
| 33 | Marketing | Campaign Revenue | DT chien dich | SUM(NeedPayAmount) per campaign | SaleOrder + PromotionCampaignSaleOrder | Link tables + Campaign.Name | daily_campaign_sales | store x day x campaign | VND | 1 don co the nhieu campaigns. |  |
| 34 | Target | Target Achievement % | % Dat muc tieu | actual_rev / target x 100 | SaleOrder + monthly_targets | NeedPayAmount; gt_weekday/weekend/holiday | monthly_targets + daily_sales_finance | store x month | % | Target nhap tay. Coverage? |  |
| 35 | Leaderboard | Revenue Rank | XH Doanh thu | RANK() ORDER BY revenue DESC | SaleOrder | NeedPayAmount | monthly_store_leaderboard | store x month | rank |  |  |
| 36 | Leaderboard | Conv Rate Rank | XH Ty le CD | RANK() ORDER BY conv_rate DESC | SaleOrder + MeasurementTicket | orders/tickets | monthly_store_leaderboard | store x month | rank |  |  |
| 37 | Leaderboard | ATV Rank | XH ATV | RANK() ORDER BY atv DESC | SaleOrder | revenue/orders | monthly_store_leaderboard | store x month | rank |  |  |
| 38 | Leaderboard | UPT Rank | XH UPT | RANK() ORDER BY upt DESC | SaleOrderItem | units/orders | monthly_store_leaderboard | store x month | rank |  |  |
| 39 | Leaderboard | Remake Rank | XH Remake | RANK() ORDER BY remake ASC | SaleOrder + MeasurementTicket | remakes/orders | monthly_store_leaderboard | store x month | rank | ASC: thap=tot |  |
| 40 | Leaderboard | Rev/Staff Rank | XH DT/NV | RANK() ORDER BY rps DESC | SaleOrder + stores | revenue/staff_count | monthly_store_leaderboard | store x month | rank |  |  |


## SHEET: POS Table Mapping (17 rows, 5 cols)

| Bang POS | Cot chinh | KPIs su dung | Join dieu kien | Filter bat buoc |
| --- | --- | --- | --- | --- |
| SaleOrder | Id, SiteId, CustomerId, CompleteAt, NeedPayAmount, DiscountAmount, SaleChannelId, EcomSourceId | Revenue, GPM, NPM, ATV, UPT, Churn, Retention, RFM, CLV, Funnel, Channel, Campaign, Target, Leaderboard | JOIN Site ON SiteId; JOIN Customer ON CustomerId | DeleteAt IS NULL AND CompleteAt IS NOT NULL |
| SaleOrderItem | Id, SaleOrderId, ProductId, Quantity, SubTotal, SubTotalCostPrice | GPM(COGS), UPT, GMROI, OOS, STR, Turnover | JOIN SaleOrder ON SaleOrderId; JOIN Product ON ProductId | DeleteAt IS NULL |
| Site | Id, Name, StoreName, SiteGroupId, ProvinceCode | Store dimension, Region | JOIN Province ON ProvinceCode | DeleteAt IS NULL |
| Customer | Id, SiteId, CurrentDebtAmount, TotalSaleAmount, LastTransactionAt | RFM, CLV, Retention, Segments | JOIN SaleOrder ON CustomerId | DeleteAt IS NULL |
| MeasurementTicket | Id, SiteId, CustomerId, IssueAt | Funnel, Remake Rate | JOIN Site ON SiteId | DeleteAt IS NULL |
| StockHistory | WarehouseId, ProductId, Quantity, EndStock, CostPrice, IsReturn | Dead Stock, Cover Days, Inventory | JOIN Warehouse ON WarehouseId | DeleteAt IS NULL |
| StockItem | WarehouseId, ProductId, InboundAt, CostPrice | Ageing, Dead Stock SKU, OOS | JOIN Warehouse ON WarehouseId | DeleteAt IS NULL |
| Warehouse | Id, SiteId, Name | Store-Kho mapping | JOIN Site ON SiteId | DeleteAt IS NULL |
| Product | Id, Code, Name, ProductCategoryId, BrandId, CostPrice | SKU dim, GMROI, ABC | JOIN Brand; JOIN ProductCategory | DeleteAt IS NULL |
| ReturnSaleOrder | Id, SiteId, CompleteAt, NeedPayAmount | Return Rate, CSAT proxy | JOIN Site ON SiteId | DeleteAt IS NULL |
| SupplierWarranty | Id, SiteId, IssueAt | Return Rate, CSAT proxy | JOIN Site ON SiteId | DeleteAt IS NULL |
| SaleChannel | Id, Name | Channel Mix | JOIN SaleOrder ON SaleChannelId | DeleteAt IS NULL |
| EcomSource | Id, ShopName | Channel Mix (online) | JOIN SaleOrder ON EcomSourceId | DeleteAt IS NULL |
| PromotionCampaign | Id, Name, Code | Campaign Performance | Via PromotionCampaignSaleOrder | DeleteAt IS NULL |
| PromotionCampaignSaleOrder | PromotionCampaignId, SaleOrderId | Campaign-Order link | JOIN both | N/A |
| Rating (ZnsDb) | Score, CreatedAt, SiteId | CSAT Real | JOIN Site ON SiteId | ZNS_PG_DSN required |


## SHEET: Validation Checklist (19 rows, 5 cols)

| # | Cau hoi can Leader validate | Domain | Trang thai | Ghi chu |
| --- | --- | --- | --- | --- |
| 1 | Doanh thu dung NeedPayAmount (sau VAT/giam gia) hay ProductAmount? | Finance |  |  |
| 2 | COGS = SubTotalCostPrice dung? Co case = 0 hoac NULL? | Finance |  |  |
| 3 | OPEX proxy 12% hop ly? Co nguon OPEX that (payroll, rent)? | Finance |  |  |
| 4 | staff_count mac dinh 12/CH - co bang headcount that? | Finance |  |  |
| 5 | CompleteAt la thoi diem ghi nhan DT chinh thuc? | Finance |  |  |
| 6 | Don huy (CancelAt) loai chua? Don doi (ExchangeParentId)? | Finance |  |  |
| 7 | Churn proxy (non-repeat) dung nghiep vu? Hay can CRM churn? | Customer |  |  |
| 8 | Remake proxy (MeasurementTicket +-14d) chinh xac? Co cot IsRemake? | Customer |  |  |
| 9 | RFM thresholds (30/60/120/365d) phu hop industry kinh mat? | Customer |  |  |
| 10 | Retention set-diff theo thang dung? Hay theo quy (kinh mat it frequent)? | Customer |  |  |
| 11 | Dead Stock % (StockHistory qty<=0) chuan? Hay SKU khong ban >90d? | Inventory |  |  |
| 12 | Stock Cover Days = EndStock/ABS(Quantity) dung? Hay AVG daily sold? | Inventory |  |  |
| 13 | MeasurementTicket du data? Bao nhieu store rong ticket? | Marketing |  |  |
| 14 | Channel fallback 'Offline/POS' khi SaleChannelId=NULL dung? | Marketing |  |  |
| 15 | CSAT ZnsDb schema Rating(Score,CreatedAt,SiteId) khop? | Quality |  |  |
| 16 | Target (monthly_targets) nguon? Nhap tay? Coverage? | Target |  |  |
| 17 | Timezone Asia/Ho_Chi_Minh cho cat ngay - don 23:59 UTC? | All |  |  |
| 18 | Soft delete (DeleteAt IS NULL) tat ca queries da filter? | All |  |  |

