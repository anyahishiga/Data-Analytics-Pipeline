-- ============================================================
-- analytics.sql  (PostgreSQL; cũng chạy được trên Redshift)
-- 15 câu truy vấn phân tích trên Star Schema:
--     fact_sales  JOIN  dim_date / dim_customer / dim_product / dim_location
--
-- Cách chạy:
--   pgAdmin : chuột phải database ecommerce_analytics > Query Tool > dán 1 query > F5
--   psql    : psql -U postgres -d ecommerce_analytics -f sql/analytics.sql
--
-- QUY ƯỚC: "doanh thu" chỉ tính đơn có status = 'Completed'.
--          Mỗi query gồm: mô tả, SQL, và ví dụ output THẬT (chạy trên dữ liệu seed 42,
--          10.000 dòng raw -> 9.427 dòng sạch). Nếu bạn đổi seed hoặc số dòng thì số sẽ khác.
-- ============================================================

-- ------------------------------------------------------------
-- 1. Total Revenue - Tổng doanh thu
-- ------------------------------------------------------------
-- Cộng total_amount của mọi đơn hàng đã hoàn tất (status = 'Completed').
-- Đơn Cancelled / Returned / Pending không được tính là doanh thu.
SELECT SUM(total_amount) AS total_revenue
FROM fact_sales
WHERE status = 'Completed';

-- Ví dụ output:
--    total_revenue
--   73714767500.00

-- ------------------------------------------------------------
-- 2. Revenue by month - Doanh thu theo tháng
-- ------------------------------------------------------------
-- JOIN fact_sales với dim_date để biết mỗi đơn thuộc tháng nào, rồi GROUP BY năm + tháng.
-- Đây là câu truy vấn Star Schema điển hình: fact (số liệu) JOIN dimension (nhãn để nhóm).
SELECT d.year,
       d.month,
       SUM(f.total_amount) AS revenue
FROM fact_sales f
JOIN dim_date d ON f.date_id = d.date_id
WHERE f.status = 'Completed'
GROUP BY d.year, d.month
ORDER BY d.year, d.month;

-- Ví dụ output:
--   year month        revenue
--   2026     1  6101825000.00
--   2026     2  7969502500.00
--   2026     3  8876555000.00
--   2026     4  7918347500.00
--   2026     5  9291980000.00
--   2026     6 10236505000.00
--   2026     7 11187360000.00
--   2026     8 12132692500.00

-- ------------------------------------------------------------
-- 3. Revenue by category - Doanh thu theo nhóm hàng
-- ------------------------------------------------------------
-- JOIN với dim_product để lấy category, GROUP BY category, sắp xếp doanh thu giảm dần.
SELECT p.category,
       SUM(f.total_amount) AS revenue
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
WHERE f.status = 'Completed'
GROUP BY p.category
ORDER BY revenue DESC;

-- Ví dụ output:
--          category        revenue
--       Electronics 61092825000.00
--   Home Appliances  7392410000.00
--           Fashion  3019170000.00
--            Sports  1128480000.00
--             Books   668715000.00
--            Beauty   413167500.00

-- ------------------------------------------------------------
-- 4. Top 10 products - 10 sản phẩm doanh thu cao nhất
-- ------------------------------------------------------------
-- Nhóm theo sản phẩm, sắp xếp doanh thu giảm dần, LIMIT 10 để chỉ lấy 10 dòng đầu.
SELECT p.product_id,
       p.product_name,
       SUM(f.total_amount) AS revenue
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
WHERE f.status = 'Completed'
GROUP BY p.product_id, p.product_name
ORDER BY revenue DESC
LIMIT 10;

-- Ví dụ output:
--   product_id       product_name        revenue
--         P001        Laptop ASUS 23113750000.00
--         P002          iPhone 15 19754900000.00
--         P003 Samsung Galaxy S24 15001200000.00
--         P010     Vacuum Cleaner  3583230000.00
--         P004    Sony Headphones  3222975000.00
--         P009          Air Fryer  2455880000.00
--         P007      Nike Sneakers  2236375000.00
--         P008        Rice Cooker  1353300000.00
--         P015   Badminton Racket   777420000.00
--         P006        Women Dress   558057500.00

-- ------------------------------------------------------------
-- 5. Top 10 customers - 10 khách hàng chi tiêu nhiều nhất
-- ------------------------------------------------------------
-- Nhóm theo khách hàng; COUNT(DISTINCT order_id) đếm số đơn, SUM(total_amount) là tổng chi tiêu.
SELECT c.customer_id,
       c.customer_name,
       COUNT(DISTINCT f.order_id) AS orders,
       SUM(f.total_amount) AS revenue
FROM fact_sales f
JOIN dim_customer c ON f.customer_id = c.customer_id
WHERE f.status = 'Completed'
GROUP BY c.customer_id, c.customer_name
ORDER BY revenue DESC, c.customer_id
LIMIT 10;

-- Ví dụ output:
--   customer_id     customer_name orders      revenue
--      CUS00381 Customer CUS00381      6 254225000.00
--      CUS00516 Customer CUS00516      6 241795000.00
--      CUS01740 Customer CUS01740      6 238495000.00
--      CUS00640 Customer CUS00640      6 236045000.00
--      CUS00275 Customer CUS00275      5 231700000.00
--      CUS01249 Customer CUS01249     11 218232500.00
--      CUS00174 Customer CUS00174      8 217580000.00
--      CUS00684 Customer CUS00684      4 217497500.00
--      CUS01986 Customer CUS01986      5 214902500.00
--      CUS01412 Customer CUS01412      7 214620000.00

-- ------------------------------------------------------------
-- 6. Revenue by city - Doanh thu theo thành phố
-- ------------------------------------------------------------
-- JOIN với dim_location để lấy tên thành phố.
SELECT l.city,
       SUM(f.total_amount) AS revenue
FROM fact_sales f
JOIN dim_location l ON f.location_id = l.location_id
WHERE f.status = 'Completed'
GROUP BY l.city
ORDER BY revenue DESC;

-- Ví dụ output:
--          city        revenue
--   Ho Chi Minh 22447417500.00
--        Ha Noi 14735680000.00
--       Da Nang  7013090000.00
--      Bien Hoa  6255992500.00
--   Thu Dau Mot  5767910000.00
--     Hai Phong  4289780000.00
--     Nha Trang  4187605000.00
--       Can Tho  4155155000.00
--      Vung Tau  2682930000.00
--           Hue  1810127500.00
--       Unknown   369080000.00

-- ------------------------------------------------------------
-- 7. Average order value (AOV) - Giá trị trung bình mỗi đơn
-- ------------------------------------------------------------
-- AOV = tổng doanh thu / số đơn hoàn tất. ROUND(..., 2) làm tròn 2 chữ số thập phân.
SELECT ROUND(SUM(total_amount) / COUNT(DISTINCT order_id), 2) AS average_order_value
FROM fact_sales
WHERE status = 'Completed';

-- Ví dụ output:
--   average_order_value
--            9781683.59

-- ------------------------------------------------------------
-- 8. Number of orders - Tổng số đơn hàng (mọi trạng thái)
-- ------------------------------------------------------------
-- Đếm số order_id khác nhau. Không lọc status nên gồm cả đơn Cancelled, Pending, Returned.
SELECT COUNT(DISTINCT order_id) AS total_orders
FROM fact_sales;

-- Ví dụ output:
--   total_orders
--           9427

-- ------------------------------------------------------------
-- 9. Number of completed orders - Số đơn hoàn tất
-- ------------------------------------------------------------
-- Giống query 8 nhưng chỉ đếm đơn có status = 'Completed'.
SELECT COUNT(DISTINCT order_id) AS completed_orders
FROM fact_sales
WHERE status = 'Completed';

-- Ví dụ output:
--   completed_orders
--               7536

-- ------------------------------------------------------------
-- 10. Number of cancelled orders - Số đơn bị huỷ
-- ------------------------------------------------------------
-- Đếm đơn có status = 'Cancelled'. Có thể chia cho query 8 để ra tỉ lệ huỷ đơn.
SELECT COUNT(DISTINCT order_id) AS cancelled_orders
FROM fact_sales
WHERE status = 'Cancelled';

-- Ví dụ output:
--   cancelled_orders
--                868

-- ------------------------------------------------------------
-- 11. Daily revenue - Doanh thu theo ngày
-- ------------------------------------------------------------
-- Nhóm theo full_date của dim_date. Mỗi ngày 1 dòng (243 dòng) nên ví dụ bên dưới chỉ hiển thị 7 dòng đầu.
SELECT d.full_date,
       SUM(f.total_amount) AS daily_revenue
FROM fact_sales f
JOIN dim_date d ON f.date_id = d.date_id
WHERE f.status = 'Completed'
GROUP BY d.full_date
ORDER BY d.full_date;

-- Ví dụ output (7 dòng đầu):
--    full_date daily_revenue
--   2026-01-01   79645000.00
--   2026-01-02  252045000.00
--   2026-01-03  152275000.00
--   2026-01-04  251727500.00
--   2026-01-05   69912500.00
--   2026-01-06  278407500.00
--   2026-01-07  203545000.00

-- ------------------------------------------------------------
-- 12. Monthly revenue growth - Tăng trưởng doanh thu theo tháng
-- ------------------------------------------------------------
-- Bước 1 (CTE 'monthly'): tính doanh thu từng tháng, giống query 2.
-- Bước 2: hàm cửa sổ LAG(revenue) lấy doanh thu của THÁNG TRƯỚC ngay trên cùng dòng.
-- growth_pct = (tháng này - tháng trước) * 100 / tháng trước. Tháng đầu tiên không có tháng trước nên là NULL.
WITH monthly AS (
    SELECT d.year,
           d.month,
           SUM(f.total_amount) AS revenue
    FROM fact_sales f
    JOIN dim_date d ON f.date_id = d.date_id
    WHERE f.status = 'Completed'
    GROUP BY d.year, d.month
)
SELECT year,
       month,
       revenue,
       LAG(revenue) OVER (ORDER BY year, month) AS previous_revenue,
       ROUND(
           (revenue - LAG(revenue) OVER (ORDER BY year, month)) * 100.0
           / LAG(revenue) OVER (ORDER BY year, month),
           2
       ) AS growth_pct
FROM monthly
ORDER BY year, month;

-- Ví dụ output:
--   year month        revenue previous_revenue growth_pct
--   2026     1  6101825000.00             NULL       NULL
--   2026     2  7969502500.00    6101825000.00      30.61
--   2026     3  8876555000.00    7969502500.00      11.38
--   2026     4  7918347500.00    8876555000.00     -10.79
--   2026     5  9291980000.00    7918347500.00      17.35
--   2026     6 10236505000.00    9291980000.00      10.16
--   2026     7 11187360000.00   10236505000.00       9.29
--   2026     8 12132692500.00   11187360000.00       8.45

-- ------------------------------------------------------------
-- 13. Best-selling products - Sản phẩm bán chạy nhất (theo SỐ LƯỢNG)
-- ------------------------------------------------------------
-- Khác query 4: query 4 xếp theo TIỀN, query này xếp theo SỐ LƯỢNG bán ra.
-- Sản phẩm rẻ (sách, áo) có thể bán nhiều cái nhưng doanh thu thấp, và ngược lại.
SELECT p.product_id,
       p.product_name,
       SUM(f.quantity) AS units_sold
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
WHERE f.status = 'Completed'
GROUP BY p.product_id, p.product_name
ORDER BY units_sold DESC, p.product_id
LIMIT 10;

-- Ví dụ output:
--   product_id            product_name units_sold
--         P011 Python Programming Book       1087
--         P001             Laptop ASUS       1006
--         P004         Sony Headphones       1006
--         P013                Lipstick       1002
--         P008             Rice Cooker        986
--         P002               iPhone 15        982
--         P005             Men T-Shirt        978
--         P007           Nike Sneakers        977
--         P014                Yoga Mat        960
--         P009               Air Fryer        957

-- ------------------------------------------------------------
-- 14. Average discount - Mức giảm giá trung bình
-- ------------------------------------------------------------
-- AVG(discount) là tỉ lệ (0.10 = 10 phần trăm); nhân 100 để dễ đọc. Tính trên mọi đơn hàng.
SELECT ROUND(AVG(discount) * 100, 2) AS avg_discount_pct
FROM fact_sales;

-- Ví dụ output:
--   avg_discount_pct
--               8.43

-- ------------------------------------------------------------
-- 15. Revenue by payment method - Doanh thu theo phương thức thanh toán
-- ------------------------------------------------------------
-- Nhóm theo payment_method (cột này nằm ngay trong fact_sales).
SELECT payment_method,
       COUNT(DISTINCT order_id) AS orders,
       SUM(total_amount) AS revenue
FROM fact_sales
WHERE status = 'Completed'
GROUP BY payment_method
ORDER BY revenue DESC;

-- Ví dụ output:
--   payment_method orders        revenue
--          Banking   2648 25924140000.00
--      Credit Card   1869 17788387500.00
--             Cash   1534 16009542500.00
--         E-Wallet   1485 13992697500.00

