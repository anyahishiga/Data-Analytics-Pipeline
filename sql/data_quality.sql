-- data_quality.sql
-- PostgreSQL / AWS Redshift
-- Data quality checks for the orders table.

SELECT check_name,
total_rows,
invalid_rows
FROM (

```
-- 1. Duplicate order IDs
SELECT 1 AS check_no,
       'duplicate_order_id' AS check_name,
       COUNT(*) AS total_rows,
       COUNT(*) - COUNT(DISTINCT order_id) AS invalid_rows
FROM orders

UNION ALL

-- 2. Null customer IDs
SELECT 2,
       'null_customer_id',
       COUNT(*),
       COALESCE(
           SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END),
           0
       )
FROM orders

UNION ALL

-- 3. Null product IDs
SELECT 3,
       'null_product_id',
       COUNT(*),
       COALESCE(
           SUM(CASE WHEN product_id IS NULL THEN 1 ELSE 0 END),
           0
       )
FROM orders

UNION ALL

-- 4. Invalid quantity
SELECT 4,
       'quantity_le_0',
       COUNT(*),
       COALESCE(
           SUM(CASE WHEN quantity <= 0 THEN 1 ELSE 0 END),
           0
       )
FROM orders

UNION ALL

-- 5. Invalid unit price
SELECT 5,
       'unit_price_le_0',
       COUNT(*),
       COALESCE(
           SUM(CASE WHEN unit_price <= 0 THEN 1 ELSE 0 END),
           0
       )
FROM orders

UNION ALL

-- 6. Negative discount
SELECT 6,
       'discount_lt_0',
       COUNT(*),
       COALESCE(
           SUM(CASE WHEN discount < 0 THEN 1 ELSE 0 END),
           0
       )
FROM orders

UNION ALL

-- 7. Discount greater than 100%
SELECT 7,
       'discount_gt_1',
       COUNT(*),
       COALESCE(
           SUM(CASE WHEN discount > 1 THEN 1 ELSE 0 END),
           0
       )
FROM orders

UNION ALL

-- 8. Invalid order status
SELECT 8,
       'invalid_status',
       COUNT(*),
       COALESCE(
           SUM(
               CASE
                   WHEN status IS NULL
                        OR status NOT IN (
                            'Completed',
                            'Pending',
                            'Cancelled',
                            'Returned'
                        )
                   THEN 1
                   ELSE 0
               END
           ),
           0
       )
FROM orders

UNION ALL

-- 9. Invalid payment method
SELECT 9,
       'invalid_payment_method',
       COUNT(*),
       COALESCE(
           SUM(
               CASE
                   WHEN payment_method IS NULL
                        OR payment_method NOT IN (
                            'Banking',
                            'Credit Card',
                            'Cash',
                            'E-Wallet'
                        )
                   THEN 1
                   ELSE 0
               END
           ),
           0
       )
FROM orders
```

) AS checks
ORDER BY check_no;
