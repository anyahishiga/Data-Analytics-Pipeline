-- build_star_schema.sql
-- PostgreSQL
-- Load data from orders into the Star Schema.

-- Reset Star Schema
TRUNCATE TABLE
fact_sales,
dim_customer,
dim_product,
dim_date,
dim_location
RESTART IDENTITY;

-- 1. Customer Dimension
INSERT INTO dim_customer (customer_id, customer_name)
SELECT DISTINCT
customer_id,
'Customer ' || customer_id
FROM orders;

-- 2. Product Dimension
INSERT INTO dim_product (
product_id,
product_name,
category
)
SELECT
product_id,
MIN(product_name),
MIN(category)
FROM orders
GROUP BY product_id;

-- 3. Date Dimension
INSERT INTO dim_date (
date_id,
full_date,
day,
month,
quarter,
year
)
SELECT DISTINCT
CAST(TO_CHAR(order_date, 'YYYYMMDD') AS INTEGER),
order_date,
CAST(EXTRACT(DAY FROM order_date) AS INTEGER),
CAST(EXTRACT(MONTH FROM order_date) AS INTEGER),
CAST(EXTRACT(QUARTER FROM order_date) AS INTEGER),
CAST(EXTRACT(YEAR FROM order_date) AS INTEGER)
FROM orders;

-- 4. Location Dimension
INSERT INTO dim_location (city)
SELECT DISTINCT city
FROM orders
ORDER BY city;

-- 5. Sales Fact
INSERT INTO fact_sales (
order_id,
date_id,
customer_id,
product_id,
location_id,
quantity,
unit_price,
discount,
total_amount,
payment_method,
status
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
JOIN dim_location l
ON o.city = l.city;
