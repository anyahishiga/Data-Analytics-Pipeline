# Cài đặt PostgreSQL trên Windows (để chạy pipeline ở local)

PostgreSQL là database miễn phí. Ta dùng nó ở máy của bạn để hiểu toàn bộ pipeline **trước khi** tốn tiền cho Redshift.

## Bước 1. Cài PostgreSQL

1. Tải bản cài cho Windows tại <https://www.postgresql.org/download/windows/> (nút *Download the installer* của EDB).
2. Chạy file cài đặt, giữ mặc định các mục:
   - Components: **PostgreSQL Server**, **pgAdmin 4**, **Command Line Tools** (nên tick cả 3).
   - **Password** cho user `postgres`: đặt một mật khẩu và **ghi nhớ nó** (sẽ điền vào `.env`).
   - **Port**: `5432` (mặc định).
   - Locale: mặc định.
3. Bỏ qua bước "Stack Builder" ở cuối (không cần).

Kiểm tra dịch vụ đang chạy (PowerShell):

```powershell
Get-Service *postgres*
# Status phải là Running
```

## Bước 2. Tạo database `ecommerce_analytics`

### Cách A – bằng pgAdmin (dễ nhất)

1. Mở **pgAdmin 4** → nhập mật khẩu master nếu được hỏi.
2. Ở cây bên trái: **Servers** → **PostgreSQL xx** → nhập mật khẩu `postgres` vừa đặt.
3. Chuột phải **Databases** → **Create** → **Database...**
4. **Database**: `ecommerce_analytics` → **Save**.

### Cách B – bằng SQL Shell (psql)

Mở **SQL Shell (psql)** từ Start Menu, nhấn Enter 4 lần để giữ mặc định (Server, Database, Port, Username), nhập mật khẩu, rồi gõ:

```sql
CREATE DATABASE ecommerce_analytics;
```

## Bước 3. Điền thông tin vào `.env`

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ecommerce_analytics
DB_USER=postgres
DB_PASSWORD=mat_khau_ban_da_dat
```

## Bước 4. Chạy thử

```powershell
python src/transform.py --skip-s3     # tạo data/processed/orders_clean.csv (nếu chưa có)
python src/load.py
```

Kết quả mong đợi:

```
INFO Loading database...
INFO Connecting to PostgreSQL at localhost:5432/ecommerce_analytics
INFO Creating tables (if not exist)...
INFO Read 9427 processed rows from CSV
INFO Inserted 9427 rows into table orders
INFO Building star schema...
INFO Star schema rows: {'dim_customer': 1979, 'dim_product': 15, 'dim_date': 243, 'dim_location': 11, 'fact_sales': 9427}
Inserted 9427 records into PostgreSQL.
```

> Số liệu chính xác có thể lệch một chút nếu bạn đã đổi dữ liệu giả lập.

## Bước 5. Kiểm tra dữ liệu trong pgAdmin

Chuột phải database `ecommerce_analytics` → **Query Tool**, chạy:

```sql
SELECT COUNT(*) FROM orders;           -- khớp số "Inserted ... rows"
SELECT * FROM orders LIMIT 5;
SELECT * FROM fact_sales LIMIT 5;
SELECT * FROM dim_location ORDER BY location_id;
```

Bảng nằm ở: **Databases → ecommerce_analytics → Schemas → public → Tables** (bấm chuột phải **Refresh** nếu chưa thấy).

## Lỗi thường gặp

| Thông báo | Nguyên nhân | Cách sửa |
|---|---|---|
| `Sai mat khau hoac user` (`password authentication failed`) | `DB_PASSWORD` sai | Sửa `.env` cho đúng mật khẩu đã đặt lúc cài |
| `Database 'ecommerce_analytics' chua ton tai` | Chưa tạo database | Làm Bước 2 |
| `Khong ket noi duoc toi localhost:5432` | Dịch vụ PostgreSQL chưa chạy / sai port | `Get-Service *postgres*`; nếu `Stopped`: `Start-Service <tên dịch vụ>` (mở PowerShell bằng *Run as administrator*); kiểm tra `DB_PORT` |
| `psql` không nhận diện lệnh | `psql.exe` chưa nằm trong PATH | Dùng *SQL Shell (psql)* trong Start Menu, hoặc thêm `C:\Program Files\PostgreSQL\<phiên bản>\bin` vào PATH |
| `UnicodeDecodeError` khi đọc `.env` | `.env` lưu sai encoding | Tạo/lưu `.env` bằng VS Code (UTF-8) |
| `Cannot connect... psycopg2` không tìm thấy module | Chưa kích hoạt venv hoặc chưa cài thư viện | `venv\Scripts\activate` rồi `pip install -r requirements.txt` |
