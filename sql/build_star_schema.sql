-- ============================================================
-- build_star_schema.sql  (PostgreSQL)
-- Đổ dữ liệu từ bảng phẳng "orders" sang mô hình Star Schema.
-- Chạy lại nhiều lần vẫn an toàn: mỗi lần đều xoá sạch rồi nạp lại từ đầu.
-- ============================================================

-- Xoá dữ liệu cũ. RESTART IDENTITY để sale_id và location_id đếm lại từ 1.
-- (Phải liệt kê CẢ 5 bảng trong cùng một lệnh vì fact_sales tham chiếu tới các dim.)
TRUNCATE TABLE fact_sales, dim_customer, dim_product, dim_date, dim_location RESTART IDENTITY;

-- 1) dim_customer: mỗi khách hàng 1 dòng.
--    Dữ liệu nguồn KHÔNG có tên khách, nên tạm đặt tên là "Customer CUS00001".
--    (Ngoài đời thật, tên lấy từ hệ thống CRM / bảng khách hàng.)
INSERT INTO dim_customer (customer_id, customer_name)
SELECT DISTINCT customer_id, 'Customer ' || customer_id
FROM orders;

-- 2) dim_product: mỗi sản phẩm 1 dòng.
INSERT INTO dim_product (product_id, product_name, category)
SELECT product_id, MIN(product_name), MIN(category)
FROM orders
GROUP BY product_id;

-- 3) dim_date: mỗi ngày có đơn hàng 1 dòng. date_id dạng YYYYMMDD (số nguyên).
INSERT INTO dim_date (date_id, full_date, day, month, quarter, year)
SELECT DISTINCT
    CAST(TO_CHAR(order_date, 'YYYYMMDD') AS INTEGER),
    order_date,
    CAST(EXTRACT(DAY FROM order_date) AS INTEGER),
    CAST(EXTRACT(MONTH FROM order_date) AS INTEGER),
    CAST(EXTRACT(QUARTER FROM order_date) AS INTEGER),
    CAST(EXTRACT(YEAR FROM order_date) AS INTEGER)
FROM orders;

-- 4) dim_location: mỗi thành phố 1 dòng, location_id tự tăng.
INSERT INTO dim_location (city)
SELECT DISTINCT city
FROM orders
ORDER BY city;

-- 5) fact_sales: mỗi đơn hàng 1 dòng. Thay tên thành phố bằng location_id,
--    thay order_date bằng date_id (tra trong các bảng dimension).
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
