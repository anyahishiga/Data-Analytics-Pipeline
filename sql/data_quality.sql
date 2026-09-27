-- ============================================================
-- data_quality.sql  (chạy được trên PostgreSQL và Redshift)
-- Kiểm tra chất lượng dữ liệu trong bảng "orders".
--
-- Kết quả: mỗi check là 1 dòng với 3 cột
--     check_name    tên phép kiểm tra
--     total_rows    tổng số dòng trong bảng
--     invalid_rows  số dòng vi phạm (0 = tốt)
-- src/data_quality.py sẽ thêm cột "status" (PASS nếu invalid_rows = 0, ngược lại FAIL)
-- và lưu thành file data/processed/data_quality_report.csv
--
-- Cấu trúc: 9 câu SELECT nhỏ ghép bằng UNION ALL, bọc trong 1 câu SELECT ngoài
-- để sắp xếp theo số thứ tự check_no (UNION ALL không đảm bảo thứ tự).
--
-- Nếu đổi danh sách status / payment_method trong src/config.py thì nhớ sửa ở đây.
-- Không dùng ký tự phan-tram trong file này vì Python sẽ đọc và chạy nó.
-- ============================================================

SELECT check_name, total_rows, invalid_rows
FROM (

    -- 1. Trùng order_id (số dòng "thừa": tổng dòng trừ số order_id khác nhau)
    SELECT 1 AS check_no, 'duplicate_order_id' AS check_name,
           COUNT(*) AS total_rows,
           COUNT(*) - COUNT(DISTINCT order_id) AS invalid_rows
    FROM orders

    UNION ALL
    -- 2. customer_id bị NULL
    SELECT 2, 'null_customer_id', COUNT(*),
           COALESCE(SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END), 0)
    FROM orders

    UNION ALL
    -- 3. product_id bị NULL
    SELECT 3, 'null_product_id', COUNT(*),
           COALESCE(SUM(CASE WHEN product_id IS NULL THEN 1 ELSE 0 END), 0)
    FROM orders

    UNION ALL
    -- 4. quantity <= 0
    SELECT 4, 'quantity_le_0', COUNT(*),
           COALESCE(SUM(CASE WHEN quantity <= 0 THEN 1 ELSE 0 END), 0)
    FROM orders

    UNION ALL
    -- 5. unit_price <= 0
    SELECT 5, 'unit_price_le_0', COUNT(*),
           COALESCE(SUM(CASE WHEN unit_price <= 0 THEN 1 ELSE 0 END), 0)
    FROM orders

    UNION ALL
    -- 6. discount < 0
    SELECT 6, 'discount_lt_0', COUNT(*),
           COALESCE(SUM(CASE WHEN discount < 0 THEN 1 ELSE 0 END), 0)
    FROM orders

    UNION ALL
    -- 7. discount > 1
    SELECT 7, 'discount_gt_1', COUNT(*),
           COALESCE(SUM(CASE WHEN discount > 1 THEN 1 ELSE 0 END), 0)
    FROM orders

    UNION ALL
    -- 8. status không nằm trong danh sách hợp lệ (NULL cũng tính là không hợp lệ)
    SELECT 8, 'invalid_status', COUNT(*),
           COALESCE(SUM(CASE WHEN status IS NULL
                              OR status NOT IN ('Completed', 'Pending', 'Cancelled', 'Returned')
                             THEN 1 ELSE 0 END), 0)
    FROM orders

    UNION ALL
    -- 9. payment_method không nằm trong danh sách hợp lệ
    SELECT 9, 'invalid_payment_method', COUNT(*),
           COALESCE(SUM(CASE WHEN payment_method IS NULL
                              OR payment_method NOT IN ('Banking', 'Credit Card', 'Cash', 'E-Wallet')
                             THEN 1 ELSE 0 END), 0)
    FROM orders

) AS checks
ORDER BY check_no;
