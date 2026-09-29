#  Cloud Data Analytics Pipeline for E-commerce

## Overview

This project is a **Cloud Data Analytics Pipeline** that simulates an end-to-end workflow for processing e-commerce data:

```text
Raw Data → Ingestion → Transformation → Storage → Database → Analytics → Visualization
```

The project demonstrates how raw sales data can be collected, cleaned, transformed, stored, and analyzed to generate useful business insights.

### Main Technologies

* **Python & Pandas** — Data processing and transformation
* **AWS S3** — Raw and processed data storage
* **PostgreSQL** — Database for testing and analytics
* **AWS Redshift** — Cloud Data Warehouse
* **SQL** — Data analysis
* **Power BI** — Data visualization
* **Git & GitHub** — Version control

---

##  Architecture

```text
                    CSV Dataset
                         │
                         ▼
                Python Data Ingestion
                         │
                         ▼
                  AWS S3 / raw
                         │
                         ▼
                Python + Pandas
                         │
                         ▼
                  ETL / Cleaning
                         │
                         ▼
               AWS S3 / processed
                         │
                         ▼
              PostgreSQL / Redshift
                         │
                         ▼
                   SQL Analytics
                         │
                         ▼
                  Power BI Dashboard
```

The pipeline is separated into stages to make the project easier to maintain, test, and extend.   


---

##  Dataset

The project uses a **synthetic e-commerce dataset**, where each record represents an order or sales transaction.

### Main Fields

| Field            | Description                  |
| ---------------- | ---------------------------- |
| `order_id`       | Unique order identifier      |
| `customer_id`    | Customer identifier          |
| `order_date`     | Order date                   |
| `product_id`     | Product identifier           |
| `product_name`   | Product name                 |
| `category`       | Product category             |
| `quantity`       | Number of products purchased |
| `unit_price`     | Price per product            |
| `discount`       | Applied discount             |
| `payment_method` | Payment method               |
| `city`           | Customer city                |
| `status`         | Order status                 |
| `total_amount`   | Total order value            |

The dataset may contain **missing values, duplicate records, and invalid values** to simulate common data-quality issues.

---

##  Data Processing

### 1. Extract

The pipeline reads the raw CSV dataset and uploads it to AWS S3:

```text
Local CSV
   ↓
Python
   ↓
AWS S3 / raw/
```

Keeping raw data separate allows the original dataset to be preserved before transformation.

### 2. Transform

Data is cleaned and transformed using **Python and Pandas**.

Main operations include:

* Removing duplicate records
* Handling missing values
* Validating data types
* Validating quantity and price
* Checking discount values
* Standardizing categories and cities
* Validating order status
* Calculating total order amount

```text
total_amount =
quantity × unit_price × (1 - discount)
```

The processed dataset is then stored in:

```text
AWS S3 / processed/
```

### 3. Load

Processed data can be loaded into PostgreSQL for testing and SQL analytics.

```text
Processed Data
      ↓
 PostgreSQL
      ↓
 SQL Analytics
```

For a cloud environment, AWS Redshift can be used as the Data Warehouse:

```text
AWS S3
  ↓
AWS Redshift
  ↓
SQL Analytics
```

---

##  Data Warehouse

The project uses a simple **Star Schema** for analytical queries.

```text
                   dim_customer
                        │
                        │
dim_product ───── fact_sales ───── dim_date
                        │
                        │
                  dim_location
```

### Fact Table

#### `fact_sales`

Contains sales transaction information such as:

* Quantity
* Unit price
* Discount
* Total amount
* Customer
* Product
* Date
* Location

### Dimension Tables

| Table          | Description                         |
| -------------- | ----------------------------------- |
| `dim_customer` | Customer information                |
| `dim_product`  | Product, product ID, and category   |
| `dim_date`     | Date, day, month, quarter, and year |
| `dim_location` | City and location information       |

---

##  SQL Analytics

SQL is used to analyze the processed data and answer business questions such as:

* What is the total revenue?
* How does revenue change by month?
* Which products sell the most?
* Which categories generate the most revenue?
* Which cities have the highest sales?
* What is the average order value?
* Which customers generate the most revenue?
* Which payment methods are used most often?

SQL scripts are located in:

```text
sql/
├── create_tables.sql
├── analytics.sql
└── data_quality.sql
```

---

##  Power BI Dashboard

The processed data can be connected to **Power BI** to create a sales analytics dashboard.

The dashboard focuses on:

### Overview

* Total Revenue
* Total Orders
* Average Order Value
* Total Customers

### Product Analysis

* Top-selling products
* Revenue by category
* Quantity sold

### Customer Analysis

* Top customers
* Revenue by customer
* Orders by customer

### Location Analysis

* Revenue by city
* Orders by city

---

##  Data Quality

Data quality checks are performed before loading data into the database.

The pipeline checks for:

```text
Duplicate Order IDs
        ↓
Missing Customer IDs
        ↓
Missing Product IDs
        ↓
Invalid Quantities
        ↓
Invalid Prices
        ↓
Invalid Discounts
        ↓
Invalid Order Status
        ↓
Invalid Payment Methods
```

Invalid records are handled according to the type of data-quality issue to reduce the impact of bad data on analytics results.

---

##  Project Structure

```text
cloud-data-pipeline/
│
├── data/
│   ├── raw/
│   │   └── orders.csv
│   │
│   └── processed/
│       └── orders_clean.csv
│
├── src/
│   ├── config.py
│   ├── generate_data.py
│   ├── ingest.py
│   ├── transform.py
│   ├── load.py
│   └── pipeline.py
│
├── sql/
│   ├── create_tables.sql
│   ├── analytics.sql
│   └── data_quality.sql
│
├── tests/
│   └── test_pipeline.py
│
├── logs/
│
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

---

##  Installation & Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd cloud-data-pipeline
```

### 2. Create a Virtual Environment

Windows:

```powershell
python -m venv venv
```

Activate the environment:

```powershell
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file:

```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=ap-southeast-1
S3_BUCKET_NAME=your_bucket_name

DB_HOST=localhost
DB_PORT=5432
DB_NAME=ecommerce_analytics
DB_USER=postgres
DB_PASSWORD=your_password
```

> **Never commit `.env` or AWS credentials to GitHub.**

Make sure `.env` is included in `.gitignore`.

---

##  Running the Pipeline

### Generate Dataset

```bash
python src/generate_data.py
```

The generated dataset will be saved to:

```text
data/raw/orders.csv
```

### Run the Pipeline

```bash
python src/pipeline.py
```

The main workflow is:

```text
Generate / Read Data
        ↓
Data Ingestion
        ↓
Upload Raw Data
        ↓
Data Transformation
        ↓
Data Quality Check
        ↓
Upload Processed Data
        ↓
Load Database
        ↓
SQL Analytics
```

---

## Future Improvements

Possible improvements for future versions include:

* [ ] Add automated pipeline scheduling
* [ ] Improve data-quality validation
* [ ] Add automated testing
* [ ] Add monitoring and alerting
* [ ] Improve Power BI dashboard
* [ ] Integrate AWS Glue
* [ ] Move the Data Warehouse fully to AWS Redshift
* [ ] Add real-time data streaming with Apache Kafka
* [ ] Add sales forecasting using Machine Learning

---


##  Author

**Huy**

This project was created for learning and practicing:

**Cloud Computing • Data Engineering • Data Analytics • SQL • Business Intelligence**

> This is a learning project. The e-commerce dataset is synthetic and does not contain real customer information.

**Project started:** July 25, 2026
