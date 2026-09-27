-- create_tables.sql
-- PostgreSQL
-- Creates the tables for the ecommerce_analytics database.

-- 1. Source Table
CREATE TABLE IF NOT EXISTS orders (
order_id        VARCHAR(20)   PRIMARY KEY,
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

-- 2. Star Schema

-- Customer Dimension
CREATE TABLE IF NOT EXISTS dim_customer (
customer_id     VARCHAR(20)  PRIMARY KEY,
customer_name   VARCHAR(100)
);

-- Product Dimension
CREATE TABLE IF NOT EXISTS dim_product (
product_id      VARCHAR(20)  PRIMARY KEY,
product_name    VARCHAR(100),
category        VARCHAR(50)
);

-- Date Dimension
CREATE TABLE IF NOT EXISTS dim_date (
date_id         INTEGER      PRIMARY KEY,
full_date       DATE         NOT NULL,
day             INTEGER      NOT NULL,
month           INTEGER      NOT NULL,
quarter         INTEGER      NOT NULL,
year            INTEGER      NOT NULL
);

-- Location Dimension
CREATE TABLE IF NOT EXISTS dim_location (
location_id     SERIAL       PRIMARY KEY,
city            VARCHAR(50)  NOT NULL UNIQUE
);

-- Sales Fact
CREATE TABLE IF NOT EXISTS fact_sales (
sale_id         SERIAL        PRIMARY KEY,
order_id        VARCHAR(20)   NOT NULL,
date_id         INTEGER       NOT NULL REFERENCES dim_date(date_id),
customer_id     VARCHAR(20)   NOT NULL REFERENCES dim_customer(customer_id),
product_id      VARCHAR(20)   NOT NULL REFERENCES dim_product(product_id),
location_id     INTEGER       NOT NULL REFERENCES dim_location(location_id),
quantity        INTEGER       NOT NULL,
unit_price      NUMERIC(14,2) NOT NULL,
discount        NUMERIC(5,4)  NOT NULL,
total_amount    NUMERIC(16,2) NOT NULL,
payment_method  VARCHAR(30),
status          VARCHAR(20)
);
