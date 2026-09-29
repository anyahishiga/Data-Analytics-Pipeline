# Power BI Dashboard

Power BI Desktop chỉ chạy trên **Windows** và miễn phí: tải từ Microsoft Store (tìm "Power BI Desktop") hoặc từ <https://powerbi.microsoft.com/desktop/>.

Điều kiện: đã chạy pipeline thành công, PostgreSQL có 5 bảng star schema (`fact_sales`, `dim_customer`, `dim_product`, `dim_date`, `dim_location`).

---

## 1. Kết nối dữ liệu

### 1A. Kết nối PostgreSQL (local)

1. Mở Power BI Desktop → **Home → Get data → More... →** gõ `PostgreSQL` → chọn **PostgreSQL database** → **Connect**.
2. Nhập:
   - **Server**: `localhost:5432`
   - **Database**: `ecommerce_analytics`
   - **Data Connectivity mode**: **Import** (dữ liệu nhỏ, chạy nhanh)
3. Tab **Database**: User `postgres`, Password (mật khẩu trong `.env`) → **Connect**.
4. Cửa sổ **Navigator**: tick 5 bảng `fact_sales`, `dim_customer`, `dim_product`, `dim_date`, `dim_location` (không cần bảng `orders`) → **Load**.

> Nếu Power BI báo *"This connector requires one or more additional components to be installed"*: cài **Npgsql** (tìm "Npgsql releases" trên GitHub, tải file `.msi`, khi cài chọn tính năng **Npgsql GAC Installation**), rồi khởi động lại Power BI Desktop.
>
> **Cách dự phòng không cần driver:** **Get data → Text/CSV** → chọn `data/processed/orders_clean.csv`. Khi đó bạn chỉ có một bảng phẳng; các biểu đồ vẫn làm được, chỉ thay `fact_sales[...]` bằng cột của bảng đó.

### 1B. Kết nối Amazon Redshift (sau khi làm Phase 8)

1. **Get data → Amazon Redshift**.
2. **Server**: endpoint của workgroup (dạng `pipeline-wg.123456789012.ap-southeast-1.redshift-serverless.amazonaws.com:5439`), **Database**: `ecommerce_analytics`, mode **Import**.
3. Tab **Database**: user `admin` + mật khẩu → chọn 5 bảng trong schema `ecommerce` → **Load**.
4. Lỗi timeout thường do chưa bật *Publicly accessible* hoặc security group chưa mở cổng 5439 cho IP của bạn (xem `REDSHIFT_GUIDE.md`).

---

## 2. Xây mô hình dữ liệu (Model view)

Bấm biểu tượng **Model** (cột bên trái). Power BI thường tự nhận diện quan hệ theo tên cột; hãy kiểm tra đúng 4 quan hệ sau (kéo cột từ fact sang dimension nếu thiếu):

| Từ (nhiều) | Đến (một) | Cardinality | Filter direction |
|---|---|---|---|
| `fact_sales[date_id]` | `dim_date[date_id]` | Many to one (*:1) | Single |
| `fact_sales[customer_id]` | `dim_customer[customer_id]` | Many to one | Single |
| `fact_sales[product_id]` | `dim_product[product_id]` | Many to one | Single |
| `fact_sales[location_id]` | `dim_location[location_id]` | Many to one | Single |

Bố cục hình ngôi sao: `fact_sales` ở giữa, 4 bảng dim xung quanh.

### Cột tính toán cho trục thời gian

Ở bảng `dim_date` → **Table tools → New column**:

```DAX
Year-Month = FORMAT(dim_date[full_date], "YYYY-MM")
```

(chuỗi `2026-01`, `2026-02`... sắp xếp theo thứ tự chữ cái cũng chính là theo thời gian).

### Measures (DAX)

Chuột phải bảng `fact_sales` → **New measure**, tạo lần lượt:

```DAX
Total Revenue = CALCULATE(SUM(fact_sales[total_amount]), fact_sales[status] = "Completed")

Total Orders = DISTINCTCOUNT(fact_sales[order_id])

Completed Orders = CALCULATE(DISTINCTCOUNT(fact_sales[order_id]), fact_sales[status] = "Completed")

Average Order Value = DIVIDE([Total Revenue], [Completed Orders])

Total Customers = DISTINCTCOUNT(fact_sales[customer_id])

Quantity Sold = CALCULATE(SUM(fact_sales[quantity]), fact_sales[status] = "Completed")
```

**Vì sao dùng measure thay vì kéo cột `total_amount` trực tiếp?** Measure tự tính lại theo *bộ lọc hiện tại* (đang chọn tháng nào, thành phố nào...). Và `CALCULATE(..., status = "Completed")` đảm bảo doanh thu **chỉ tính đơn hoàn tất**, giống các truy vấn trong `analytics.sql`.

**Đối chiếu để chắc chắn đúng:** so với dữ liệu mẫu, `Total Revenue` phải bằng query 1 của `analytics.sql` (73.714.767.500), `Average Order Value` = 9.781.683,59, `Total Orders` = 9.427. Nếu lệch, kiểm tra lại quan hệ và measure.

---

## 3. Tạo dashboard (4 trang)

Cách thêm biểu đồ chung: bấm vào vùng trống của trang → ở khung **Visualizations** chọn loại biểu đồ → kéo cột/measure từ khung **Data** vào các ô **Axis / Values / Legend...** như hướng dẫn dưới.

Đổi tên trang: chuột phải tab ở đáy → **Rename**. Thêm trang: nút **+**.

### PAGE 1 – Executive Overview

| Thành phần | Loại visual | Cấu hình |
|---|---|---|
| **Total Revenue** | Card | Fields: `Total Revenue` |
| **Total Orders** | Card | Fields: `Total Orders` |
| **Average Order Value** | Card | Fields: `Average Order Value` |
| **Total Customers** | Card | Fields: `Total Customers` |
| **Revenue by Month** | Line chart (hoặc Clustered column) | X-axis: `dim_date[Year-Month]`; Y-axis: `Total Revenue` |
| **Revenue by Category** | Donut chart (hoặc Bar) | Legend/Axis: `dim_product[category]`; Values: `Total Revenue` |
| **Revenue by City** | Clustered bar chart | Y-axis: `dim_location[city]`; X-axis: `Total Revenue` (khung **Visual → Sort** theo Total Revenue giảm dần) |

Gợi ý: thêm **Slicer** (Visualizations → Slicer) với `dim_product[category]` để lọc cả trang.

### PAGE 2 – Product Analytics

| Thành phần | Loại visual | Cấu hình |
|---|---|---|
| **Top Products** | Clustered bar chart | Y-axis: `dim_product[product_name]`; X-axis: `Total Revenue`. Khung **Filters** → kéo `product_name` vào → *Filter type* = **Top N** → *Show items* **Top** `10` → *By value* kéo `Total Revenue` → **Apply filter** |
| **Sales by Category** | Clustered column chart | X-axis: `dim_product[category]`; Y-axis: `Total Revenue` |
| **Quantity Sold** | Bar chart | Y-axis: `dim_product[product_name]`; X-axis: `Quantity Sold` (có thể áp Top N tương tự) |

### PAGE 3 – Customer Analytics

Có gần 2.000 khách hàng nên **luôn dùng Top N**, nếu không biểu đồ không đọc được.

| Thành phần | Loại visual | Cấu hình |
|---|---|---|
| **Top Customers** | Table | Columns: `dim_customer[customer_id]`, `Total Revenue`, `Total Orders`. Filter **Top N = 10** theo `Total Revenue` |
| **Revenue by Customer** | Bar chart | Y-axis: `dim_customer[customer_id]`; X-axis: `Total Revenue`; Top N = 10 |
| **Orders by Customer** | Bar chart | Y-axis: `dim_customer[customer_id]`; X-axis: `Total Orders`; Top N = 10 theo `Total Orders` |

### PAGE 4 – Location Analytics

| Thành phần | Loại visual | Cấu hình |
|---|---|---|
| **Revenue by City** | Clustered bar chart | Y-axis: `dim_location[city]`; X-axis: `Total Revenue` |
| **Orders by City** | Clustered bar chart | Y-axis: `dim_location[city]`; X-axis: `Total Orders` |

> Vì tên thành phố trong dữ liệu **không dấu**, biểu đồ bản đồ (Map) có thể không định vị đúng; dùng bar chart cho an toàn. Thành phố `Unknown` là các đơn thiếu thông tin thành phố (được điền `Unknown` ở bước transform).

### Định dạng cho đẹp

- Số lớn: chọn visual → **Format → Callout value / Data labels → Display units = Millions** (hoặc *Billions* cho card doanh thu).
- Thêm **Title** cho từng visual; đặt cùng bảng màu; căn hàng thẳng bằng **Format → Align**.
- Xem thử: **View → Page view → Fit to page**.

## 4. Lưu và cập nhật

- **File → Save as** `ecommerce_dashboard.pbix`.
- Khi chạy lại pipeline và có dữ liệu mới: bấm **Home → Refresh**. (Chế độ Import lưu bản sao dữ liệu trong file `.pbix`, nên phải Refresh.)
- **Đưa lên GitHub (tuỳ chọn):** chụp ảnh từng trang dashboard lưu vào `docs/images/` và chèn vào README. File `.pbix` chỉ lưu *địa chỉ máy chủ và tên database* (không lưu mật khẩu), nhưng vẫn nên xem lại trước khi commit, đặc biệt nếu đã nối tới endpoint Redshift thật.
