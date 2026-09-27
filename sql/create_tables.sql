-- ============================================================
-- create_tables.sql  (PostgreSQL)
-- Tạo bảng cho database "ecommerce_analytics".
-- File này CHẠY ĐƯỢC NHIỀU LẦN: dùng CREATE TABLE IF NOT EXISTS nên không xoá dữ liệu cũ.
-- (src/load.py tự chạy file này; bạn cũng có thể chạy tay trong pgAdmin.)
-- Lưu ý: không dùng ký tự phan-tram trong file này vì Python sẽ đọc và chạy nó.
-- ============================================================

-- ------------------------------------------------------------
-- PHẦN 1: BẢNG PHẲNG "orders" (Phase 5)
-- Nhận nguyên dữ liệu đã làm sạch từ data/processed/orders_clean.csv
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    order_id        VARCHAR(20)   PRIMARY KEY,
    customer_id     VARCHAR(20)   NOT NULL,
    order_date      DATE          NOT NULL,
    product_id      VARCHAR(20)   NOT NULL,
    product_name    VARCHAR(100),
    category        VARCHAR(50),
    quantity        INTEGER       NOT NULL,
    unit_price      NUMERIC(14,2) NOT NULL,
    discount        NUMERIC(5,4)  NOT NULL,   -- 0.10 nghĩa là giảm 10 phần trăm
    payment_method  VARCHAR(30),
    city            VARCHAR(50),
    status          VARCHAR(20),
    total_amount    NUMERIC(16,2) NOT NULL
);

-- ------------------------------------------------------------
-- PHẦN 2: STAR SCHEMA (Phase 6)
--   4 bảng dimension (mô tả: ai, cái gì, khi nào, ở đâu)
--   1 bảng fact      (số liệu bán hàng, mỗi dòng = 1 đơn hàng)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id     VARCHAR(20)  PRIMARY KEY,
    customer_name   VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS dim_product (
    product_id      VARCHAR(20)  PRIMARY KEY,
    product_name    VARCHAR(100),
    category        VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_id         INTEGER      PRIMARY KEY,   -- dạng YYYYMMDD, ví dụ 20260115
    full_date       DATE         NOT NULL,
    day             INTEGER      NOT NULL,
    month           INTEGER      NOT NULL,
    quarter         INTEGER      NOT NULL,
    year            INTEGER      NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_location (
    location_id     SERIAL       PRIMARY KEY,   -- tự tăng 1, 2, 3, ...
    city            VARCHAR(50)  NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS fact_sales (
    sale_id         SERIAL        PRIMARY KEY,
    order_id        VARCHAR(20)   NOT NULL,
    date_id         INTEGER       NOT NULL REFERENCES dim_date (date_id),
    customer_id     VARCHAR(20)   NOT NULL REFERENCES dim_customer (customer_id),
    product_id      VARCHAR(20)   NOT NULL REFERENCES dim_product (product_id),
    location_id     INTEGER       NOT NULL REFERENCES dim_location (location_id),
    quantity        INTEGER       NOT NULL,
    unit_price      NUMERIC(14,2) NOT NULL,
    discount        NUMERIC(5,4)  NOT NULL,
    total_amount    NUMERIC(16,2) NOT NULL,
    payment_method  VARCHAR(30),   -- thêm so với thiết kế gốc, cần cho query 15
    status          VARCHAR(20)    -- thêm so với thiết kế gốc, cần cho query 9, 10
);
