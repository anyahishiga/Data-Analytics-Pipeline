-- analytics.sql
-- PostgreSQL / AWS Redshift
-- 15 analytical queries using Star Schema
-- Revenue is calculated only from Completed orders.

-- 1. Total Revenue
SELECT SUM(total_amount) AS total_revenue
FROM fact_sales
WHERE status = 'Completed';

-- 2. Revenue by Month
SELECT d.year,
d.month,
SUM(f.total_amount) AS revenue
FROM fact_sales f
JOIN dim_date d ON f.date_id = d.date_id
WHERE f.status = 'Completed'
GROUP BY d.year, d.month
ORDER BY d.year, d.month;

-- 3. Revenue by Category
SELECT p.category,
SUM(f.total_amount) AS revenue
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
WHERE f.status = 'Completed'
GROUP BY p.category
ORDER BY revenue DESC;

-- 4. Top 10 Products by Revenue
SELECT p.product_id,
p.product_name,
SUM(f.total_amount) AS revenue
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
WHERE f.status = 'Completed'
GROUP BY p.product_id, p.product_name
ORDER BY revenue DESC
LIMIT 10;

-- 5. Top 10 Customers by Revenue
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

-- 6. Revenue by City
SELECT l.city,
SUM(f.total_amount) AS revenue
FROM fact_sales f
JOIN dim_location l ON f.location_id = l.location_id
WHERE f.status = 'Completed'
GROUP BY l.city
ORDER BY revenue DESC;

-- 7. Average Order Value
SELECT ROUND(
SUM(total_amount) / COUNT(DISTINCT order_id),
2
) AS average_order_value
FROM fact_sales
WHERE status = 'Completed';

-- 8. Total Orders
SELECT COUNT(DISTINCT order_id) AS total_orders
FROM fact_sales;

-- 9. Completed Orders
SELECT COUNT(DISTINCT order_id) AS completed_orders
FROM fact_sales
WHERE status = 'Completed';

-- 10. Cancelled Orders
SELECT COUNT(DISTINCT order_id) AS cancelled_orders
FROM fact_sales
WHERE status = 'Cancelled';

-- 11. Daily Revenue
SELECT d.full_date,
SUM(f.total_amount) AS daily_revenue
FROM fact_sales f
JOIN dim_date d ON f.date_id = d.date_id
WHERE f.status = 'Completed'
GROUP BY d.full_date
ORDER BY d.full_date;

-- 12. Monthly Revenue Growth
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
(revenue - LAG(revenue) OVER (ORDER BY year, month))
* 100.0
/ LAG(revenue) OVER (ORDER BY year, month),
2
) AS growth_pct
FROM monthly
ORDER BY year, month;

-- 13. Top 10 Best-Selling Products by Quantity
SELECT p.product_id,
p.product_name,
SUM(f.quantity) AS units_sold
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
WHERE f.status = 'Completed'
GROUP BY p.product_id, p.product_name
ORDER BY units_sold DESC, p.product_id
LIMIT 10;

-- 14. Average Discount
SELECT ROUND(AVG(discount) * 100, 2) AS avg_discount_pct
FROM fact_sales;

-- 15. Revenue by Payment Method
SELECT payment_method,
COUNT(DISTINCT order_id) AS orders,
SUM(total_amount) AS revenue
FROM fact_sales
WHERE status = 'Completed'
GROUP BY payment_method
ORDER BY revenue DESC;
