-- ============================================================
-- redshift_load.sql  (AMAZON REDSHIFT - dùng ở Phase 8)
-- Đây là phiên bản Redshift của: create_tables.sql + nạp dữ liệu + build_star_schema.sql
--
-- CẢNH BÁO CHI PHÍ: Redshift KHÔNG miễn phí. Đọc docs/REDSHIFT_GUIDE.md TRƯỚC khi tạo.
--
-- Cách dùng (trong Redshift Query Editor v2, đã kết nối vào workgroup của bạn):
--   1. Thay 2 giá trị bên dưới:
--        <YOUR_BUCKET>    -> tên bucket S3 của bạn
--        <IAM_ROLE_ARN>   -> ARN của IAM Role gắn cho Redshift (có quyền đọc S3)
--        <AWS_REGION>     -> region của bucket, ví dụ ap-southeast-1
--   2. Chạy từng khối (bôi đen -> Run), theo thứ tự từ trên xuống.
--
-- Khác biệt so với PostgreSQL (rất hay bị hỏi khi phỏng vấn):
--   - Không có SERIAL      -> dùng  INTEGER IDENTITY(1,1)
--   - PRIMARY KEY / FOREIGN KEY chỉ mang tính THÔNG TIN, Redshift KHÔNG bắt buộc (không chặn
--     dữ liệu trùng) -> vì vậy các check trong data_quality.sql rất quan trọng.
--   - Nạp dữ liệu bằng lệnh COPY từ S3 (nhanh hơn INSERT rất nhiều).
--   - TRUNCATE không có RESTART IDENTITY -> ở đây dùng DROP TABLE IF EXISTS rồi tạo lại.
-- ============================================================

-- ------------------------------------------------------------
-- KHỐI 1: Tạo schema riêng và dùng nó
-- ------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS ecommerce;
SET search_path TO ecommerce;

-- ------------------------------------------------------------
-- KHỐI 2: Xoá bảng cũ (nếu có) và tạo lại. Xoá fact TRƯỚC, dim SAU.
-- ------------------------------------------------------------
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_location;
DROP TABLE IF EXISTS orders;

CREATE TABLE orders (
    order_id        VARCHAR(20)   NOT NULL,
    customer_id     VARCHAR(20)   NOT NULL,
    order_date      DATE          NOT NULL,
    product_id      VARCHAR(20)   NOT NULL,
    product_name    VARCHAR(100),
    category        VARCHAR(50),
    quantity        INTEGER       NOT NULL,
    unit_price      NUMERIC(14,2) NOT NULL,
    discount        NUMERIC(5,4)  NOT NULL,
    payment_method  VARCHAR(30),
    city            VARCHAR(50),
    status          VARCHAR(20),
    total_amount    NUMERIC(16,2) NOT NULL
);

CREATE TABLE dim_customer (
    customer_id     VARCHAR(20)  NOT NULL PRIMARY KEY,
    customer_name   VARCHAR(100)
);

CREATE TABLE dim_product (
    product_id      VARCHAR(20)  NOT NULL PRIMARY KEY,
    product_name    VARCHAR(100),
    category        VARCHAR(50)
);

CREATE TABLE dim_date (
    date_id         INTEGER      NOT NULL PRIMARY KEY,
    full_date       DATE         NOT NULL,
    day             INTEGER      NOT NULL,
    month           INTEGER      NOT NULL,
    quarter         INTEGER      NOT NULL,
    year            INTEGER      NOT NULL
);

CREATE TABLE dim_location (
    location_id     INTEGER IDENTITY(1,1) PRIMARY KEY,
    city            VARCHAR(50)  NOT NULL
);

CREATE TABLE fact_sales (
    sale_id         INTEGER IDENTITY(1,1) PRIMARY KEY,
    order_id        VARCHAR(20)   NOT NULL,
    date_id         INTEGER       NOT NULL REFERENCES dim_date (date_id),
    customer_id     VARCHAR(20)   NOT NULL REFERENCES dim_customer (customer_id),
    product_id      VARCHAR(20)   NOT NULL REFERENCES dim_product (product_id),
    location_id     INTEGER       NOT NULL REFERENCES dim_location (location_id),
    quantity        INTEGER       NOT NULL,
    unit_price      NUMERIC(14,2) NOT NULL,
    discount        NUMERIC(5,4)  NOT NULL,
    total_amount    NUMERIC(16,2) NOT NULL,
    payment_method  VARCHAR(30),
    status          VARCHAR(20)
);

-- ------------------------------------------------------------
-- KHỐI 3: Nạp dữ liệu từ S3 vào bảng orders bằng COPY
--   - File s3://<bucket>/processed/orders_clean.csv do pipeline của bạn tạo ra
--   - IGNOREHEADER 1 : bỏ qua dòng tiêu đề
--   - Thứ tự cột trong CSV phải khớp thứ tự cột của bảng orders
-- ------------------------------------------------------------
COPY orders
FROM 's3://<YOUR_BUCKET>/processed/orders_clean.csv'
IAM_ROLE '<IAM_ROLE_ARN>'
FORMAT AS CSV
IGNOREHEADER 1
REGION '<AWS_REGION>';

-- Kiểm tra: phải ra đúng số dòng của orders_clean.csv (ví dụ 9427)
SELECT COUNT(*) AS rows_loaded FROM orders;

-- Nếu COPY báo lỗi, xem chi tiết bằng:
--   SELECT * FROM sys_load_error_detail ORDER BY start_time DESC LIMIT 10;

-- ------------------------------------------------------------
-- KHỐI 4: Dựng Star Schema (giống build_star_schema.sql)
-- ------------------------------------------------------------
INSERT INTO dim_customer (customer_id, customer_name)
SELECT DISTINCT customer_id, 'Customer ' || customer_id
FROM orders;

INSERT INTO dim_product (product_id, product_name, category)
SELECT product_id, MIN(product_name), MIN(category)
FROM orders
GROUP BY product_id;

INSERT INTO dim_date (date_id, full_date, day, month, quarter, year)
SELECT DISTINCT
    CAST(TO_CHAR(order_date, 'YYYYMMDD') AS INTEGER),
    order_date,
    CAST(EXTRACT(DAY FROM order_date) AS INTEGER),
    CAST(EXTRACT(MONTH FROM order_date) AS INTEGER),
    CAST(EXTRACT(QUARTER FROM order_date) AS INTEGER),
    CAST(EXTRACT(YEAR FROM order_date) AS INTEGER)
FROM orders;

INSERT INTO dim_location (city)
SELECT DISTINCT city
FROM orders;

INSERT INTO fact_sales (
    order_id, date_id, customer_id, product_id, location_id,
    quantity, unit_price, discount, total_amount, payment_method, status
)
SELECT
    o.order_id,
    CAST(TO_CHAR(o.order_date, 'YYYYMMDD') AS INTEGER),
    o.customer_id,
    o.product_id,
    l.location_id,
    o.quantity,
    o.unit_price,
    o.discount,
    o.total_amount,
    o.payment_method,
    o.status
FROM orders o
JOIN dim_location l ON o.city = l.city;

-- Kiểm tra số dòng các bảng
SELECT 'orders' AS table_name, COUNT(*) AS row_count FROM orders
UNION ALL SELECT 'dim_customer', COUNT(*) FROM dim_customer
UNION ALL SELECT 'dim_product',  COUNT(*) FROM dim_product
UNION ALL SELECT 'dim_date',     COUNT(*) FROM dim_date
UNION ALL SELECT 'dim_location', COUNT(*) FROM dim_location
UNION ALL SELECT 'fact_sales',   COUNT(*) FROM fact_sales;

-- ------------------------------------------------------------
-- KHỐI 5: Chạy data quality và analytics
--   Mở sql/data_quality.sql và sql/analytics.sql, dán vào Query Editor và chạy
--   (giữ nguyên câu SET search_path TO ecommerce; ở phiên làm việc hiện tại).
--   Hai file này viết sao cho chạy được cả trên PostgreSQL lẫn Redshift.
-- ------------------------------------------------------------

-- ------------------------------------------------------------
-- KHỐI 6: DỌN DẸP để không bị tính tiền (chạy khi học xong)
--   Xoá schema trong database (tuỳ chọn):
--       DROP SCHEMA ecommerce CASCADE;
--   NHƯNG việc quan trọng nhất là XOÁ workgroup + namespace Redshift Serverless
--   trên AWS Console (xem docs/REDSHIFT_GUIDE.md, mục "Dọn dẹp").
-- ------------------------------------------------------------
