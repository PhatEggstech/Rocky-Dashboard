# PO Checklist - Production Patch 2026-08-24

## Pham vi va ket qua deploy

| Muc | Ket qua |
| --- | --- |
| Moi truong | Production `https://rockyhmkmcp.share.zrok.io/mcp` |
| Release code | `14c4930`, `6366ddd`, `69862c7` tren nhanh `mcp-rocky-ai` |
| Cach deploy | Backup runtime, compile 3 module, restart mot lan; public health sau deploy = HTTP 200 |
| Smoke qua public endpoint | OAuth, `tools/list` (57 tools), WMS, POS, Dashboard Revenue, Dashboard Overview, Business Summary: PASS |
| Canh bao | Ket qua live thay doi theo thoi diem. PO doi chieu cung khoang ngay, cung site va cung thoi diem refresh Dashboard. |

## Quy uoc doi chieu bat buoc

1. Ngay `date_from`/`date_to` duoc quy doi theo `Asia/Ho_Chi_Minh`: tu `00:00:00.000` den `23:59:59.999`.
2. KPI giao dien chi doc payload Dashboard API; MCP khong tu cong, tru, lam tron hay thay the field Dashboard.
3. `traceId` thay doi giua hai request la binh thuong va khong duoc dung de ket luan sai lech du lieu.
4. `get_revenue_legacy`, POS raw SQL va cac KPI phu thuoc Dashboard PG khong phai nguon de PO doi chieu widget Dashboard.

## Checklist tool da sua va da len production

| # | Tool / luong | Use case PO can test | Nguon chuan va endpoint | Cong thuc / quy tac tra ve | Ket qua production | Cach PO validate |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `get_dashboard_order_overview` | Hoi "so don, gia tri don, thuc thu, con phai thu hom nay/hom qua/tuan nay" | Rocky Lens Dashboard API: `POST /Admin/Dashboard/Order/Overview` | Tra nguyen `data.totalOrder`, `data.totalAmount`, `data.totalPaidAmount`, `data.totalLeftAmount`. Khong tinh lai trong MCP. | PASS, HTTP 200 qua public smoke | Chon cung ky tren man `Tinh hinh kinh doanh`; so 4 card phai bang cac field tren. |
| 2 | `get_dashboard_revenue` | Hoi "doanh so", "HMK bao nhieu", "Khac bao nhieu", "so don ban/don tra" | Rocky Lens Dashboard API: `POST /Admin/Dashboard/Revenue` | Doc duy nhat `data.summary.all`: `totalRevenue`, `hmkRevenue`, `otherRevenue`, `numOrder`, `numReturnOrder`. Khong lay `thuc thu` tu tool nay. | PASS, HTTP 200 qua public smoke | Chon man `Doanh so`, cung ky/site; doi chieu dong `summary.all`. |
| 3 | `get_revenue_by_source` | Hoi tach HMK vs Khac, App/Portal/System | Alias tuong thich cua Dashboard Revenue API | Cong thuc = tool #2; `compatibility_alias = get_dashboard_revenue`. Khong dung cho cau hoi tong quan. | PASS; payload data bang `get_dashboard_revenue` sau khi bo qua `meta.traceId` | Goi hai tool cung tham so; doi chieu `data`/`summary.all`, khong doi chieu `traceId`. |
| 4 | `get_tinh_hinh_kinh_doanh` | Hoi "tinh hinh kinh doanh", "tong quan hom nay" | 3 Dashboard API read-only endpoints: `Order/Overview`, `Order/BySite`, `Order/ByStaff` | `overview = Order/Overview`; `by_site = Order/BySite`; `staff = Order/ByStaff`; `source = rocky_dashboard_api`. Da bo cach cu tron doanh thu staff tu POS. | PASS, `business_summary_source=rocky_dashboard_api`, `business_summary_has_staff_error=false` | Doi chieu lan luot 4 card, bieu do chi nhanh va danh sach staff voi cung ky tren Dashboard. |
| 5 | `query_raw_pos_sql_tool` | Admin can doi chieu ky thuat SELECT tren POS, ke ca CTE | POS PostgreSQL read-only | Chap nhan mot cau `SELECT` hoac `WITH ... SELECT`; bo qua chuoi/comment khi kiem tra. Chan `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `ALTER`, `DROP`, `TRUNCATE`, `COPY`, `CALL`, `DO`, `GRANT`, `REVOKE` va nhieu statement. | PASS: `WITH probe AS (SELECT 1 AS value) SELECT value FROM probe` tra `value=1` | Dung CTE read-only tren schema da duoc mo ta; thu `SELECT 1; SELECT 2` phai bi chan. |
| 6 | `track_tool` (quan sat runtime cho moi tool) | Phan biet tool thanh cong va tool tra payload loi | Log MCP runtime | `failure = result.error OR result.ok is false OR result.code >= 400`. Failure ghi `[FAILURE]`, khong ghi `[SUCCESS]`. | Unit regression PASS trong bo `32 passed` | Tao request sai tham so tren staging; log phai la `[FAILURE]`, khong phai `[SUCCESS]`. |
| 7 | Role BOD va fallback goi tool | BOD xem tong hop Dashboard nhung khong xem du lieu nhay cam | Role allow-list trong MCP | BOD duoc: `get_dashboard_sales_by_customer`, `get_dashboard_debt_overview`, tong quan/doanh so/chi nhanh/san pham. BOD bi chan: raw SQL, WMS/kho, gia von/gia nhap, chi tiet cong no. Khi goi `get_debt`/`get_customers`, tra `alternatives` ve tool Dashboard tong hop. | Da deploy policy; unit regression PASS | Dang nhap BOD: goi `get_dashboard_debt_overview` phai duoc; `query_raw_pos_sql_tool` va `get_inventory_live` phai 403. |
| 8 | `scripts/smoke_local_oauth.py` | Nghiem thu OAuth va contract doanh thu sau moi deploy | Public MCP endpoint va Dashboard API | Script phai so sanh `get_revenue_by_source` voi `get_dashboard_revenue`, bo qua `meta.traceId`; khong dung tool cu `get_revenue`. Co assertion cho Business Summary. | PASS qua public endpoint sau deploy | Chay smoke voi tai khoan test tren may MCP; tat ca truong `*_tool_ok` va `revenue_matches_dashboard` phai `true`. |
| 9 | `scripts/provision_local_user.py` | Tranh cap tai khoan vao sai auth store | Cau hinh `MCP_AUTH_BACKEND` | Chi ghi SQLite khi backend = `sqlite`. Neu backend khac thi dung va bao loi ro rang, khong tao tai khoan "ao". | Da deploy script maintenance | Khi runtime la `dashboard_pg`, script phai dung truoc khi ghi database local. |

## Test case da cover trong ban va

| Ma | Case | Ky vong |
| --- | --- | --- |
| RT-01 | `SELECT` don | Duoc phep |
| RT-02 | `WITH ... SELECT` | Duoc phep |
| RT-03 | Dau `;` nam trong string literal | Duoc phep |
| RT-04 | DML/DDL trong CTE hoac query thuong | Bi chan |
| RT-05 | Nhieu statement (`SELECT 1; SELECT 2`) | Bi chan |
| RT-06 | Tool tra `{"error": ...}` | Tracker ghi `[FAILURE]` |
| RT-07 | BOD yeu cau cong no chi tiet | Tra 403 kem alternative tong hop |
| RT-08 | BOD yeu cau SQL raw/kho WMS | Tra 403 |
| RT-09 | Doanh thu tach nguon vs Dashboard Revenue | Cung payload nghiep vu, bo qua `traceId` |
| RT-10 | Business Summary | 3 phan deu tu Dashboard API, khong tron POS staff |

## Ngoai pham vi patch nay

| Nhom | Trang thai | Ly do / hanh dong tiep theo |
| --- | --- | --- |
| KPI cu doc truc tiep `DASHBOARD_PG_DSN` (vi du GPM, NPM, ATV, UPT, RPS, picker legacy, Telegram mapping) | Chua duoc xac nhan la KPI Dashboard | Ket noi Dashboard PG upstream da timeout. Se migrate tung tool sang Dashboard API, POS hoac WMS sau khi chot mapping nghiep vu; khong dung de doi chieu widget UI hien tai. |
| Nghiem thu BOD bang tai khoan that | Can chay bo sung | Policy va unit test da pass. Can mot tai khoan BOD dang hoat dong tren auth backend production de chay case RT-07, RT-08 end-to-end. |

## Duyet PO

| Hang muc | Ket qua PO | Nguoi duyet | Ngay |
| --- | --- | --- | --- |
| KPI Tong quan |  |  |  |
| Doanh so HMK/Khac |  |  |  |
| Tinh hinh kinh doanh va staff |  |  |  |
| Raw POS SQL read-only |  |  |  |
| Phan quyen BOD |  |  |  |
