---
title: HMK Vision Dashboard - Phân Tích Source Code Chi Tiết
created: 2026-05-08
author: AI-assisted
last_updated: 2026-05-13
updated_by: AI-assisted
status: active
---

# HMK Vision Dashboard - Phân Tích Source Code Chi Tiết

## 1. Tổng Quan Dự Án

| Thuộc tính | Giá trị |
|------------|---------|
| **Tên dự án** | HMK Vision Dashboard |
| **Mô tả** | AI-Powered Business Performance Dashboard cho Ban Giám Đốc (BOD) chuỗi cửa hàng kính mắt HMK |
| **Platform** | Google AI Studio App (React + Vite) |
| **Lĩnh vực** | Chuỗi bán lẻ kính mắt (Hàng Mắt Kính - HMK) hoạt động tại Việt Nam |
| **Đối tượng sử dụng** | BOD / C-Level & Store Manager |

---

## 2. Cấu Trúc Thư Mục (Directory Tree)

```
hmk-dashboard-ai-main/
├── .env.example              # Biến môi trường (GEMINI_API_KEY, APP_URL)
├── .gitignore                # Git ignore rules
├── README.md                 # Hướng dẫn cơ bản
├── index.html                # Entry point HTML (SPA)
├── metadata.json             # Metadata cho Google AI Studio
├── package.json              # Dependencies & scripts
├── package-lock.json         # Lock file
├── tsconfig.json             # TypeScript configuration
├── vite.config.ts            # Vite build configuration
└── src/
    ├── main.tsx              # React DOM mount point
    ├── App.tsx               # App shell chính, logic điều hướng
    ├── index.css             # Tailwind CSS import
    ├── lib/
    │   └── utils.ts          # Utility function: cn() (clsx + tailwind-merge)
    ├── components/
    │   ├── Sidebar.tsx       # Thanh điều hướng bên trái
    │   ├── Header.tsx        # Header bar (search, filter, user info)
    │   └── Breadcrumb.tsx    # Breadcrumb navigation + nút Back
    └── pages/
        ├── ExecutiveSummary.tsx        # Trang tổng quan cho BOD
        ├── SalesMarketing.tsx          # Trang Sales & Marketing
        ├── InventorySupplyChain.tsx    # Trang Inventory & Supply Chain
        ├── QualityCLV.tsx              # Trang Quality & Customer Lifetime Value
        └── details/
            ├── StoreRevenueDetail.tsx    # Chi tiết doanh thu từng cửa hàng
            ├── GPMDetail.tsx             # Chi tiết Gross Profit Margin
            ├── GPMBrandDetail.tsx        # GPM phân tích theo thương hiệu
            ├── StoreProfile.tsx          # Hồ sơ chẩn đoán cửa hàng
            ├── CustomerProfileDetail.tsx # Hồ sơ phân khúc khách hàng
            ├── InventoryKPIDetail.tsx    # Chi tiết KPI tồn kho
            └── InventoryValueDetail.tsx  # Phân tích giá trị tồn kho
```

---

## 3. Technology Stack

| Layer | Công nghệ | Phiên bản | Vai trò |
|-------|-----------|-----------|---------|
| **Framework** | React | 19 | UI library chính |
| **Build Tool** | Vite | 6.2 | Dev server + bundler |
| **Language** | TypeScript | 5.8 | Type safety |
| **Styling** | Tailwind CSS | 4.1 | Utility-first CSS (via `@tailwindcss/vite` plugin) |
| **Charts** | Recharts | 3.8 | Biểu đồ (Line, Bar, Pie, Treemap, Scatter, Composed, Area) |
| **Icons** | Lucide React | 0.546 | Icon library |
| **Animation** | Motion | 12.23 | Animation library (đã import nhưng chưa sử dụng) |
| **Utilities** | clsx + tailwind-merge | - | Merge class names an toàn |
| **AI SDK** | @google/genai | 1.29 | Gemini AI (đã cài nhưng chưa tích hợp trong code) |
| **Server** | Express | - | Deployment (chưa có server file) |

---

## 4. Configuration Files

### `vite.config.ts`
```typescript
- Plugins: tailwindcss(), react()
- Path alias: "@/" → "./src/"
- HMR: có thể tắt qua biến DISABLE_HMR
```

### `tsconfig.json`
```json
- Target: ES2022
- Module: ESNext
- JSX: react-jsx
- Path alias: "@/*" → "./src/*"
- noEmit: true (chỉ type-check, không build)
```

### `.env.example`
```
GEMINI_API_KEY=   → API key cho Gemini AI (chưa được sử dụng trong code)
APP_URL=          → URL của ứng dụng khi deploy
```

### `metadata.json`
```json
{
  "app_name": "HMK Vision Dashboard",
  "description": "AI-Powered Business Performance Dashboard for HMK BOD",
  "platform": "aistudio"
}
```

---

## 5. Kiến Trúc & Cơ Chế Điều Hướng (Navigation Architecture)

### 5.1 Phương pháp điều hướng

Ứng dụng **KHÔNG sử dụng React Router**. Toàn bộ điều hướng được quản lý bằng **state-based routing** trong `App.tsx` thông qua 3 state variables:

```typescript
const [currentPage, setCurrentPage] = useState('executive');    // Tab chính
const [detailPage, setDetailPage] = useState<string | null>(null); // Trang chi tiết
const [selectedBrand, setSelectedBrand] = useState<string | null>(null); // Brand context
```

### 5.2 Luồng điều hướng (Navigation Flow)

```
┌─────────────────────────────────────────────────────────────────┐
│                         App.tsx                                   │
│                                                                   │
│  currentPage ────► Xác định tab nào hiển thị                     │
│  detailPage  ────► Nếu != null, hiển thị trang chi tiết thay vì │
│                    trang chính                                    │
│  selectedBrand ──► Truyền context brand cho GPMBrandDetail       │
│                                                                   │
│  Luồng:                                                          │
│  1. Sidebar click → setCurrentPage(page), setDetailPage(null)    │
│  2. Main page click → setDetailPage('store-revenue' | 'gpm'...)  │
│  3. Detail page Back → setDetailPage(null)                       │
│  4. Store profile: "store-profile:TênCH:tab" (colon-delimited)  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 Các giá trị detailPage và mapping

| detailPage value | Component render | Nguồn điều hướng |
|------------------|-----------------|-------------------|
| `null` | Trang chính theo currentPage | Sidebar click / Back button |
| `'store-revenue'` | `<StoreRevenueDetail>` | ExecutiveSummary |
| `'gpm'` | `<GPMDetail>` | ExecutiveSummary |
| `'gpm-brand'` | `<GPMBrandDetail>` | GPMDetail |
| `'store-profile:*:*'` | `<StoreProfile>` | ExecutiveSummary heatmap/Top-Bottom |
| `'customer-new'` | `<CustomerProfileDetail type="new">` | SalesMarketing |
| `'customer-returning'` | `<CustomerProfileDetail type="returning">` | SalesMarketing |
| `'customer-inactive'` | `<CustomerProfileDetail type="inactive">` | SalesMarketing |
| `'inventory-value'` | `<InventoryKPIDetail type="value">` | InventorySupplyChain |
| `'inventory-turnover'` | `<InventoryKPIDetail type="turnover">` | InventorySupplyChain |
| `'inventory-oos'` | `<InventoryKPIDetail type="oos">` | InventorySupplyChain |
| `'inventory-str'` | `<InventoryKPIDetail type="str">` | InventorySupplyChain |

---

## 6. Component Hierarchy (Cây Component)

```
<React.StrictMode>
└── <App>
    ├── <Sidebar 
    │       currentPage={currentPage}
    │       onNavigate={(page) => { setCurrentPage(page); setDetailPage(null) }}
    │   />
    └── <div className="flex-1 flex flex-col">
         ├── <Header />
         └── <main>
              └── renderPage() → Một trong các component sau:
                   │
                   ├── [Main Pages - khi detailPage === null]
                   │   ├── <ExecutiveSummary onNavigateDetail={setDetailPage} />
                   │   ├── <SalesMarketing onNavigateDetail={setDetailPage} />
                   │   ├── <InventorySupplyChain onNavigateDetail={setDetailPage} />
                   │   └── <QualityCLV onNavigateDetail={setDetailPage} />
                   │
                   └── [Detail Pages - khi detailPage !== null]
                       ├── <StoreRevenueDetail onBack={() => setDetailPage(null)} />
                       ├── <GPMDetail 
                       │       onBack={...} 
                       │       onNavigateBrand={(brand) => { setSelectedBrand(brand); setDetailPage('gpm-brand') }}
                       │   />
                       ├── <GPMBrandDetail 
                       │       brandName={selectedBrand}
                       │       onBack={() => setDetailPage('gpm')}
                       │       onNavigateHome={() => setDetailPage(null)}
                       │   />
                       ├── <StoreProfile 
                       │       storeName={parsed from detailPage}
                       │       initialTab={parsed from detailPage}
                       │       onBack={() => setDetailPage(null)}
                       │   />
                       ├── <CustomerProfileDetail 
                       │       type={'new'|'returning'|'inactive'}
                       │       onBack={() => setDetailPage(null)}
                       │   />
                       └── <InventoryKPIDetail
                               type={'value'|'turnover'|'oos'|'str'}
                               onBack={() => setDetailPage(null)}
                           />
```

---

## 7. Quản Lý State (State Management)

### Chiến lược: **Local State Only** (không có global state)

- **Không sử dụng** Redux, Zustand, Context API hay bất kỳ state management library nào
- Mỗi component quản lý state riêng qua `useState`
- **Props drilling**: Dữ liệu truyền từ trên xuống (top-down), callback truyền từ dưới lên (bottom-up)
- **Dữ liệu**: Toàn bộ là mock data hardcoded bên trong mỗi component

### Pattern chung của mỗi page:
```typescript
const [activeTab, setActiveTab] = useState('tab1');   // Tab nội bộ
const [viewMode, setViewMode] = useState('default');  // Chế độ hiển thị
const [expandedRows, setExpandedRows] = useState<string[]>([]); // Tree table state
```

---

## 8. Luồng Dữ Liệu (Data Flow)

```
┌─────────────────────────────────────────────────┐
│              HIỆN TẠI: Mock Data                 │
│                                                   │
│  Mỗi component tự chứa data hardcoded:          │
│                                                   │
│  const mockStores = [                            │
│    { name: 'HMK Gò Vấp', revenue: 850, ... },   │
│    { name: 'HMK Quận 1', revenue: 920, ... },    │
│    ...                                           │
│  ];                                              │
│                                                   │
│  ► KHÔNG có API calls                            │
│  ► KHÔNG có fetch/axios                          │
│  ► KHÔNG có backend connection                   │
│  ► "AI Insights" là static text                  │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│              DỰ KIẾN: Gemini AI Integration      │
│                                                   │
│  @google/genai đã được cài nhưng CHƯA sử dụng   │
│  GEMINI_API_KEY configured trong .env            │
│  Có thể dùng để:                                │
│  - Generate AI Insights động                    │
│  - Chatbot hỏi đáp dữ liệu                     │
│  - Dự báo (Forecast)                            │
└─────────────────────────────────────────────────┘
```

---

## 9. Shared Components (Components Dùng Chung)

### 9.1 `Sidebar.tsx`

**Chức năng:** Thanh điều hướng cố định bên trái

**Cấu trúc:**
- Logo HMK + tên "HMK Vision"
- **Nhóm BOD / C-LEVEL:**
  - Executive Summary (LayoutDashboard icon)
  - Sales & Marketing (TrendingUp icon)
  - Inventory & Supply Chain (Package icon)
  - Quality & CLV (Heart icon)
- **Nhóm STORE MANAGER:**
  - Live Operations (Activity icon)
  - Quality & Service Control (Shield icon)
- Footer: Settings + Logout (chỉ UI, chưa có logic)

**Props:**
```typescript
{
  currentPage: string;          // Highlight active item
  onNavigate: (page: string) => void;  // Callback khi click menu
}
```

**Visual:** Dark theme (slate-900 background), active item có emerald-500 left border + emerald background

---

### 9.2 `Header.tsx`

**Chức năng:** Thanh header cố định phía trên

**Thành phần:**
- Search bar (UI only, không có logic search)
- Date range badge ("T5/2025")
- Notification bell (có badge số 3)
- User avatar "BA" + tên "BOD Admin / C-Level"

**Props:** Không có props (self-contained component)

---

### 9.3 `Breadcrumb.tsx`

**Chức năng:** Hiển thị đường dẫn điều hướng + nút quay lại

**Props:**
```typescript
{
  items: { label: string; onClick?: () => void }[];  // Breadcrumb items
  onBack: () => void;                                 // Callback nút Back
}
```

---

### 9.4 `lib/utils.ts`

**Chức năng:** Utility function `cn()` - merge Tailwind classes an toàn

```typescript
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

---

## 10. Chi Tiết Từng Tab / Page

---

### 10.1 TAB: Executive Summary (`ExecutiveSummary.tsx`)

**Mục đích:** Cung cấp cái nhìn tổng quan nhanh cho BOD về tình hình kinh doanh toàn chuỗi.

**Các section:**

#### A. AI Executive Briefing
- Khung hiển thị các bullet points insight do AI tạo (hiện là static text)
- Nội dung: Tóm tắt revenue growth, profit margin, tình trạng vận hành
- Icon: Sparkles (indigo theme) biểu thị AI-generated content

#### B. KPI Scorecards (3 thẻ)
| KPI | Giá trị | Chi tiết |
|-----|---------|----------|
| Revenue MTD | 12.5B VND | Sparkline chart, +8.2% YoY, progress bar vs target |
| GPM | 62.4% | Sparkline chart, +1.2pp vs LY |
| Target Achievement | 105% | Sparkline chart, 32/38 stores đạt target |

- Click vào Revenue → navigate đến `StoreRevenueDetail`
- Click vào GPM → navigate đến `GPMDetail`

#### C. Top Gainers / Top Losers
- 2 bảng song song: Top stores tăng trưởng tốt nhất và kém nhất
- Hiển thị: Tên store, % growth, revenue
- Click vào store → navigate đến `StoreProfile`

#### D. Revenue by Channel (Pie Chart)
- Offline: 55%
- Web: 15%
- Shopee: 20%
- TikTok Shop: 10%

#### E. Performance Heatmap
- Ma trận: Store × Ngày trong tuần
- Toggle giữa "% Target" và "Conv. Rate"
- Màu sắc: Xanh (tốt) → Đỏ (cần chú ý)
- Hover: Tooltip hiện AI insight cho ô đó
- Click ô đỏ → navigate đến `StoreProfile` với tab tương ứng

**Tương tác:**
```
ExecutiveSummary
  ├── Click KPI Revenue → onNavigateDetail('store-revenue')
  ├── Click KPI GPM → onNavigateDetail('gpm')
  ├── Click Store name → onNavigateDetail('store-profile:StoreName:traffic')
  └── Click Heatmap cell → onNavigateDetail('store-profile:StoreName:tab')
```

---

### 10.2 TAB: Sales & Marketing (`SalesMarketing.tsx`)

**Mục đích:** Phân tích hiệu quả bán hàng, conversion funnel và hiệu quả marketing campaigns.

**Các section:**

#### A. Conversion Funnel
- Biểu đồ phễu 3 bước:
  - Walk-in: 10,000 lượt
  - Eye Exam: 6,500 lượt (65% conversion)
  - Close Bill: 4,200 lượt (64.6% conversion)
- Hiển thị dropoff rate giữa các bước

#### B. Campaign Performance (Scatter Plot)
- Trục X: Customer Acquisition Cost (CAC)
- Trục Y: Revenue generated
- Kích thước bubble: Budget spent
- Mỗi bubble = 1 campaign
- Giúp BOD đánh giá ROI từng chiến dịch marketing

#### C. Customer Composition (Stacked Bar Chart)
- Trục X: Tháng (6 tháng gần nhất)
- Trục Y: Số lượng khách
- Phân loại: New (xanh) / Returning (vàng) / Inactive (đỏ)
- Có trendline overlay
- **Click vào từng segment** → navigate đến `CustomerProfileDetail`

**Tương tác:**
```
SalesMarketing
  ├── Click "New" segment → onNavigateDetail('customer-new')
  ├── Click "Returning" segment → onNavigateDetail('customer-returning')
  └── Click "Inactive" segment → onNavigateDetail('customer-inactive')
```

---

### 10.3 TAB: Inventory & Supply Chain (`InventorySupplyChain.tsx`)

**Mục đích:** Quản lý tồn kho, chuỗi cung ứng và hiệu quả sử dụng vốn hàng tồn.

**Các section:**

#### A. KPI Cards (4 thẻ, tất cả clickable)
| KPI | Giá trị | Ý nghĩa |
|-----|---------|----------|
| Total Inventory Value | 45.2B VND | Tổng giá trị hàng tồn |
| Inventory Turnover | 45 ngày | Số ngày xoay vòng hàng tồn |
| OOS Rate | 3.5% | Tỷ lệ hết hàng (Out of Stock) |
| Sell-through Rate | 82% | Tỷ lệ bán hết hàng nhập |

#### B. GMROI Treemap
- Gross Margin Return on Investment
- Visualization dạng treemap: Kích thước = Value, Màu = Hiệu quả
- Phân theo category (Gọng kính, Tròng kính, Kính râm, Phụ kiện)

#### C. Inventory Ageing (Bar Chart)
- Phân bổ tồn kho theo độ tuổi:
  - 0-30 ngày
  - 31-60 ngày
  - 61-90 ngày
  - 91-180 ngày
  - >180 ngày
- Highlight vùng >90 ngày (hàng chậm luân chuyển)

#### D. ABC Classification (Table)
| Hạng | % SKU | % Revenue | % Value | Action |
|------|-------|-----------|---------|--------|
| A | 20% | 70% | 50% | Priority replenish |
| B | 30% | 20% | 30% | Standard order |
| C | 50% | 10% | 20% | Reduce/Clearance |

**Tương tác:**
```
InventorySupplyChain
  ├── Click "Inventory Value" card → onNavigateDetail('inventory-value')
  ├── Click "Turnover" card → onNavigateDetail('inventory-turnover')
  ├── Click "OOS Rate" card → onNavigateDetail('inventory-oos')
  └── Click "Sell-through" card → onNavigateDetail('inventory-str')
```

---

### 10.4 TAB: Quality & CLV (`QualityCLV.tsx`)

**Mục đích:** Đo lường chất lượng dịch vụ, sự hài lòng khách hàng và giá trị vòng đời khách hàng.

**Các section:**

#### A. KPI Cards (4 thẻ)
| KPI | Giá trị | Ý nghĩa |
|-----|---------|----------|
| CSAT | 4.6/5 | Customer Satisfaction Score |
| Remake Rate | 4.2% | Tỷ lệ phải làm lại kính |
| Retention Rate | 35% | Tỷ lệ khách quay lại |
| Average CLV | 2.5M VND | Giá trị vòng đời trung bình |

#### B. CSAT Trend (Line Chart) + Satisfaction Distribution (Pie Chart)
- Line chart: CSAT theo tháng (12 tháng)
- Pie chart: Phân bổ điểm đánh giá (5★, 4★, 3★, 2★, 1★)

#### C. Remake Pareto Chart (Composed Chart)
- Bar: Số lượng remake theo nguyên nhân (giảm dần)
  - Sai số đo
  - Sai loại tròng
  - Hỏng frame
  - Lỗi lắp ráp
  - Khác
- Line: % tích lũy (Pareto curve)
- Áp dụng nguyên tắc 80/20

#### D. Cohort Retention Matrix (Table)
- Hàng: Tháng cohort (tháng đăng ký/mua đầu tiên)
- Cột: Month 0, Month 1, Month 2, ... Month 6
- Giá trị: % retention rate
- Màu sắc: Đậm = retention cao, nhạt = thấp

#### E. RFM Segmentation (Visual Blocks)
- Phân khúc khách hàng theo Recency-Frequency-Monetary:
  - **Champions** (xanh lá): Mua gần đây, mua nhiều, chi nhiều
  - **Loyal Customers** (xanh dương): Mua thường xuyên
  - **At Risk** (cam): Từng mua nhiều nhưng lâu không quay lại
  - **Hibernating** (đỏ): Không hoạt động lâu
- Hiển thị: Số lượng + % tổng + Revenue contribution

**Tương tác:** Tab này chủ yếu hiển thị thông tin, không có drill-down navigation đến detail pages.

---

## 11. Chi Tiết Các Trang Detail

---

### 11.1 `StoreRevenueDetail.tsx`

**Mục đích:** Drill-down chi tiết doanh thu từng cửa hàng trong chuỗi.

**3 chế độ hiển thị (View Modes):**
1. **Performance** - Xếp hạng stores theo hiệu suất (sortable)
2. **Regional** - Nhóm theo khu vực (HCM, Hà Nội, Miền Trung, ...)
3. **Tier** - Nhóm theo loại store (Flagship / Standard / New)

**Bảng dữ liệu (Table):**
| Cột | Mô tả |
|-----|--------|
| Rank | Thứ hạng |
| Store | Tên cửa hàng |
| Actual Revenue | Doanh thu thực |
| Target | Mục tiêu |
| AI Forecast | Dự báo AI (static) |
| % Target | % đạt target |
| Growth | % tăng trưởng |
| AI Insights | Nhận xét AI (static text) |

**Tính năng:**
- Sortable columns
- Export dropdown (Excel / PDF / CSV) - chỉ UI, chưa có logic export thật
- Search/filter stores

---

### 11.2 `GPMDetail.tsx`

**Mục đích:** Phân tích chi tiết biên lợi nhuận gộp (Gross Profit Margin) theo cấu trúc cây.

**Các section:**

#### A. Waterfall Chart
- Mô tả cấu trúc lợi nhuận:
  - Gross Revenue → trừ COGS → trừ Promotions → = Gross Profit
- Mỗi bước có bar riêng biệt

#### B. Expandable Tree Table
- Cấu trúc phân cấp: **Category → Brand → SKU**
- Mỗi row hiển thị: GPM actual, GPM target, variance, AI insight
- Double-click vào Brand → navigate đến `GPMBrandDetail`

**Tương tác:**
```
GPMDetail
  ├── Expand/Collapse tree rows
  ├── Double-click brand → onNavigateBrand(brandName)
  └── Back button → onBack()
```

---

### 11.3 `GPMBrandDetail.tsx`

**Mục đích:** Phân tích sâu GPM cho một thương hiệu cụ thể (ví dụ: Rayban, Oakley).

**Các section:**

#### A. GPM Trend Line (6 tháng)
- Line chart: GPM thực tế vs Target line
- Highlight tháng nào dưới target

#### B. Cash Cows Table
- SKU có biên lợi nhuận cao nhất
- Cột: SKU, Revenue, GPM%, Quantity sold, Trend

#### C. Money Burners Table
- SKU có biên lợi nhuận thấp/âm
- Cột: SKU, Revenue, GPM%, Loss amount, Warning level
- Highlight đỏ cho các SKU cần hành động

#### D. Store Contribution Table
- Đóng góp GPM từ từng store cho brand này
- 4 view modes: Performance / Regional / Tier / Map

#### E. Smart Search
- Tìm kiếm SKU trong brand

---

### 11.4 `StoreProfile.tsx`

**Mục đích:** Trang chẩn đoán sức khỏe của một cửa hàng cụ thể - xác định "root cause" vấn đề.

**Cấu trúc:**

#### A. Store Header
- Tên store, địa chỉ, tier
- Alert badge (nếu có vấn đề)
- Status indicators

#### B. Diagnostic Tree (4 metric cards)
| Metric | Ý nghĩa | Ví dụ |
|--------|----------|-------|
| Traffic | Lượng khách vào store | ↓ 15% vs LM |
| Conversion | Tỷ lệ chuyển đổi | 42% (target 50%) |
| AOV | Average Order Value | 1.2M VND |
| Stock | Tình trạng kho | 3 SKU OOS |

- Hệ thống highlight 1 metric là **root cause** (viền đỏ)
- Logic: Metric nào lệch target nhiều nhất được đánh dấu

#### C. Staff Leaderboard
- **Top 3**: Nhân viên bán tốt nhất (tên, revenue, conversion rate)
- **Bottom 3**: Nhân viên cần cải thiện

#### D. Worst SKUs
- Danh sách hàng tồn lâu nhất / bán chậm nhất tại store

#### E. Analysis Tabs
| Tab | Nội dung |
|-----|----------|
| **Traffic** | Line chart traffic theo giờ/ngày + AI diagnosis text |
| **Conversion** | Bar chart conversion theo time slot + AI diagnosis |
| **Stock** | Bảng OOS items + AI diagnosis |
| **AOV** | Placeholder (chưa triển khai chi tiết) |

#### F. Fixed Action Bar (cố định dưới cùng)
- **Chat Zalo**: Mở chat với store manager
- **Assign Task**: Giao việc cho store
- **Edit Target**: Chỉnh target cho store

*Lưu ý: Các action buttons chỉ là UI, chưa có logic thực.*

---

### 11.5 `CustomerProfileDetail.tsx`

**Mục đích:** Hồ sơ chi tiết từng phân khúc khách hàng (New / Returning / Inactive).

**Props:** `type: 'new' | 'returning' | 'inactive'`

**Các section (thay đổi data theo type):**

#### A. AI Insights Panel
- Nhận xét AI về phân khúc này (static text)

#### B. 4 Metric Cards
| Metric (ví dụ type='new') | Giá trị |
|---------------------------|---------|
| Số lượng khách mới | 2,350 |
| Revenue từ khách mới | 3.2B VND |
| AOV khách mới | 1.36M VND |
| First Purchase Retention | 28% |

#### C. Demographics (Pie Chart)
- Phân bổ theo nhóm tuổi hoặc giới tính

#### D. Product Preferences (Horizontal Bar Chart)
- Sản phẩm ưa thích: Gọng kính (45%), Tròng (30%), Kính râm (15%), Phụ kiện (10%)

#### E. Time Trend (Line Chart)
- Xu hướng số lượng khách theo tháng

---

### 11.6 `InventoryKPIDetail.tsx`

**Mục đích:** Chi tiết từng KPI tồn kho khi click từ trang Inventory.

**Props:** `type: 'value' | 'turnover' | 'oos' | 'str'`

**Đặc biệt:** Khi `type === 'value'` → render `<InventoryValueDetail>` thay vì layout mặc định.

**Layout mặc định (turnover/oos/str):**
- AI Insights panel
- 4 KPI sub-cards liên quan
- Tab: Chart view / Data table view
- Chart tương ứng với KPI type

---

### 11.7 `InventoryValueDetail.tsx`

**Mục đích:** Phân tích giá trị tồn kho theo store, phát hiện "Zombie Stores" (store tồn nhiều nhưng bán ít).

**Các section:**

#### A. Scatter Plot
- Trục X: Inventory Value
- Trục Y: Revenue
- Mỗi điểm = 1 store
- Vùng highlight đỏ: "Zombies Store" zone (inventory cao, revenue thấp)
- Giúp BOD nhận diện stores cần điều chuyển hàng

#### B. AI Action Center
- Card hiển thị gợi ý hành động:
  - Đề xuất chuyển hàng từ store A → store B
  - Gợi ý clearance cho hàng tồn lâu
  - Priority actions

#### C. Expandable Tree Table
- Cấu trúc: **Region → Cluster → Store**
- Mỗi row hiển thị:
  - Inventory Value (actual)
  - Inventory Limit
  - AI Forecast (dự báo)
  - Progress bar với marker AI forecast
  - AI Action (đề xuất hành động cụ thể)

---

## 12. Sơ Đồ Tương Tác Giữa Các Component

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              APP.TSX                                      │
│   ┌─────────┐    ┌──────────────────────────────────────────────────┐   │
│   │         │    │                CONTENT AREA                        │   │
│   │         │    │  ┌────────────────────────────────────────────┐   │   │
│   │         │    │  │              HEADER.TSX                     │   │   │
│   │ SIDEBAR │    │  │  [Search] [Date] [Notification] [User]     │   │   │
│   │  .TSX   │    │  └────────────────────────────────────────────┘   │   │
│   │         │    │                                                    │   │
│   │ ┌─────┐ │    │  ┌────────────────────────────────────────────┐   │   │
│   │ │Exec │◄├────┼──┤         EXECUTIVE SUMMARY                   │   │   │
│   │ │     │ │    │  │  ┌──────┐ ┌──────┐ ┌──────┐               │   │   │
│   │ ├─────┤ │    │  │  │KPI 1 │ │KPI 2 │ │KPI 3 │               │   │   │
│   │ │Sales│◄├────┼──┤  └──┬───┘ └──┬───┘ └──────┘               │   │   │
│   │ │     │ │    │  │     │        │                              │   │   │
│   │ ├─────┤ │    │  │     ▼        ▼                              │   │   │
│   │ │Invt │◄├────┼──┤  StoreRev  GPMDetail ──► GPMBrandDetail    │   │   │
│   │ │     │ │    │  │  Detail                                     │   │   │
│   │ ├─────┤ │    │  │                                             │   │   │
│   │ │Qual │◄├────┼──┤  [Heatmap] ──► StoreProfile                │   │   │
│   │ │     │ │    │  │  [Top/Bottom] ──► StoreProfile              │   │   │
│   │ └─────┘ │    │  └────────────────────────────────────────────┘   │   │
│   │         │    │                                                    │   │
│   └─────────┘    │  ┌────────────────────────────────────────────┐   │   │
│                  │  │         SALES & MARKETING                    │   │   │
│                  │  │  [Funnel] [Campaigns] [Customer Comp.]      │   │   │
│                  │  │       │                      │               │   │   │
│                  │  │       │                      ▼               │   │   │
│                  │  │       │            CustomerProfileDetail     │   │   │
│                  │  └───────┼────────────────────────────────────┘   │   │
│                  │          │                                         │   │
│                  │  ┌───────┼────────────────────────────────────┐   │   │
│                  │  │       │   INVENTORY & SUPPLY CHAIN          │   │   │
│                  │  │  [KPI Cards] ──► InventoryKPIDetail         │   │   │
│                  │  │       │               │                     │   │   │
│                  │  │       │               ▼ (when type='value') │   │   │
│                  │  │       │         InventoryValueDetail        │   │   │
│                  │  │  [Treemap] [Ageing] [ABC Table]             │   │   │
│                  │  └────────────────────────────────────────────┘   │   │
│                  │                                                    │   │
│                  │  ┌────────────────────────────────────────────┐   │   │
│                  │  │         QUALITY & CLV                        │   │   │
│                  │  │  [KPIs] [CSAT] [Pareto] [Cohort] [RFM]     │   │   │
│                  │  │  (Không có drill-down navigation)           │   │   │
│                  │  └────────────────────────────────────────────┘   │   │
│                  └───────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 13. UI Design Patterns

### 13.1 Color System
| Element | Color |
|---------|-------|
| Sidebar background | `slate-900` (dark) |
| Content background | `slate-50` (light gray) |
| Primary accent | `emerald-500` (brand color) |
| AI indicator | `indigo-500` (purple-blue) |
| Danger/Alert | `red-500` |
| Success | `green-500` |
| Warning | `amber-500` |

### 13.2 Card Pattern
```css
bg-white border border-slate-200 rounded-2xl p-6 shadow-sm
```

### 13.3 AI Content Pattern
- Icon: `Sparkles` từ Lucide
- Background: `bg-indigo-50`
- Border: `border-indigo-200`
- Text color: `text-indigo-700`

### 13.4 Interactive Patterns
- **Hover**: Scale/shadow transition trên cards
- **Clickable cards**: Cursor pointer + hover:shadow-md
- **Active tab**: Border-bottom emerald hoặc bg-emerald-50
- **Tree table**: Expand/collapse với ChevronRight rotation

### 13.5 Responsive Design
- Grid layouts: `grid-cols-1 md:grid-cols-2 lg:grid-cols-4`
- Sidebar: Fixed width (không collapse trên mobile - chưa responsive hoàn chỉnh)

### 13.6 Language
- **Section headers**: Tiếng Anh (Executive Summary, Sales & Marketing, ...)
- **Data labels & insights**: Tiếng Việt (Doanh thu, Biên lợi nhuận, ...)
- **Mix**: Phù hợp với môi trường doanh nghiệp Việt Nam

---

## 14. Authentication & Authorization

**Hiện tại: KHÔNG CÓ**

- Header hiển thị hardcoded user "BOD Admin / C-Level"
- Sidebar có 2 nhóm menu (BOD/C-Level và Store Manager) nhưng không có logic phân quyền
- Nút Logout trong Sidebar không có onClick handler
- Không có login page, token management, hay session handling

---

## 15. Các Tính Năng Chưa Triển Khai / Placeholder

| Feature | Trạng thái |
|---------|-----------|
| Gemini AI Integration | Dependency cài, chưa có code gọi API |
| Live Operations tab | Menu item có, page chưa implement |
| Quality & Service Control tab | Menu item có, page chưa implement |
| Export (Excel/PDF/CSV) | UI button có, logic chưa implement |
| Search functionality | Search bar có, filter logic chưa implement |
| Chat Zalo (StoreProfile) | Button có, action chưa implement |
| Assign Task (StoreProfile) | Button có, action chưa implement |
| Edit Target (StoreProfile) | Button có, action chưa implement |
| Motion animations | Library imported, chưa sử dụng |
| Responsive sidebar collapse | Chưa có |
| Real data connection | Toàn bộ mock data |

---

## 16. Tóm Tắt Luồng Hoạt Động Của Ứng Dụng

```
1. User mở app → index.html load → main.tsx mount <App>
2. App render: Sidebar + Header + renderPage()
3. renderPage() check detailPage:
   - null → render main page theo currentPage
   - có giá trị → render detail page tương ứng
4. User click Sidebar item → currentPage thay đổi → re-render main page
5. User click element trong main page (KPI card, store name, heatmap cell)
   → setDetailPage(value) → re-render detail page
6. User click Back trong detail page → setDetailPage(null) → quay về main page
7. Đặc biệt: GPMDetail → GPMBrandDetail có 2 level drill-down
   (Back từ GPMBrandDetail → quay về GPMDetail, không phải main page)
```

---

## 17. Đề Xuất Phát Triển Tiếp

Dựa trên phân tích source code, các hướng phát triển tiếp theo có thể bao gồm:

1. **Tích hợp Gemini AI** - Sử dụng `@google/genai` để generate insights động thay vì static text
2. **Kết nối Backend/API** - Replace mock data bằng real API calls (REST hoặc GraphQL)
3. **React Router** - Chuyển sang proper routing để hỗ trợ URL sharing, browser history
4. **State Management** - Thêm Zustand/Redux nếu data flow phức tạp hơn
5. **Authentication** - Implement login + role-based access (BOD vs Store Manager)
6. **Implement remaining tabs** - Live Operations, Quality & Service Control
7. **Export functionality** - Implement actual Excel/PDF/CSV export
8. **Real-time data** - WebSocket cho Live Operations
9. **Mobile responsive** - Sidebar collapse, touch-friendly charts
10. **Testing** - Unit tests (Vitest) + E2E tests (Playwright)

---

## 18. Dữ liệu thật & lakehouse (KPI)

Phần trên mô tả UI với **mock data**. Khi nối FastAPI + warehouse PostgreSQL (Bronze/Silver/Gold), cách tính KPI và bảng mart tương ứng được tóm tắt trong **`datalake/README.md` → mục "KPI & dashboard"**, căn cứ:

- `docs/schema-pos-postgresql-da.md` — grain, FK lõi, data contract §12.
- `docs/schema-pos-postgresql-columns.md` — dictionary cột (255 bảng); ví dụ cầu nối funnel: bảng `MeasurementTicketSaleOrderItem`.

Đọc thêm:

- **`docs/TECHSTACK.md`** — bảng công nghệ đầy đủ (FE, BE, lakehouse, orchestration, DevOps).
- **`docs/DATA_FLOW.md`** — diagram Mermaid cho luồng end-to-end (Bronze/Silver/Gold, request UI, DAG, Docker network).
- `docs/schema-pos-postgresql-da.md` (mục 11–12), `datalake/ddl/005_seed_lineage.sql` (lineage bronze→silver→gold).
