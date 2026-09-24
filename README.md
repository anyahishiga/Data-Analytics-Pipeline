# ☁️ Cloud Data Analytics Pipeline for E-commerce

## 📌 Overview

Đây là một project **Cloud Data Analytics Pipeline** được xây dựng để mô phỏng quy trình xử lý dữ liệu e-commerce từ **raw data → data processing → storage → analytics → visualization**.

The main goal of this project is to understand how raw sales data can be transformed into useful business information through a complete data pipeline.

Project sử dụng **Python, Pandas, AWS S3, PostgreSQL, SQL và Power BI**. Dữ liệu ban đầu được lưu dưới dạng CSV, sau đó được upload lên AWS S3, cleaned và transformed bằng Python/Pandas, rồi load vào database để thực hiện analytics.

Cuối cùng, các kết quả phân tích được sử dụng để xây dựng **Power BI dashboard**.

---

## 🔄 Project Workflow

```text
                    CSV Dataset
                         │
                         ▼
              Python Data Ingestion
                         │
                         ▼
                  AWS S3 Raw Data
                         │
                         ▼
                  Python + Pandas
                         │
                    ETL Process
                         │
                         ▼
              AWS S3 Processed Data
                         │
                         ▼
             PostgreSQL / AWS Redshift
                         │
                         ▼
                   SQL Analytics
                         │
                         ▼
                Power BI Dashboard
```

Pipeline được thiết kế theo từng stage để dễ debug, test và mở rộng về sau.

---

## 🎯 Project Objectives

Mục tiêu chính của project là thực hành những kiến thức cơ bản trong **Cloud Data Engineering và Data Analytics**.

* Understand the basic concept of a cloud data pipeline.
* Practice data ingestion and processing with Python.
* Learn how to store raw and processed data using AWS S3.
* Clean and transform raw e-commerce data.
* Store structured data in a relational database.
* Practice SQL for business analysis.
* Build a simple **Data Warehouse** structure.
* Create a Power BI dashboard.
* Understand how different components work together in a data pipeline.

---

# 📊 Dataset

Project sử dụng một **synthetic e-commerce dataset**, trong đó mỗi record đại diện cho một order/sales transaction.

Một số fields chính:

| Field            | Description                   |
| ---------------- | ----------------------------- |
| `order_id`       | Unique order identifier       |
| `customer_id`    | Customer identifier           |
| `order_date`     | Date of the order             |
| `product_id`     | Product identifier            |
| `product_name`   | Product name                  |
| `category`       | Product category              |
| `quantity`       | Number of products purchased  |
| `unit_price`     | Price of one product          |
| `discount`       | Discount applied to the order |
| `payment_method` | Payment method                |
| `city`           | Customer city                 |
| `status`         | Order status                  |
| `total_amount`   | Total order value             |

Dataset có thể chứa **missing values, duplicate records và invalid values**.

Những lỗi này được tạo intentionally để test phần **Data Quality và Data Cleaning** của pipeline.

---

# 🛠️ Technologies

| Technology       | Purpose                        |
| ---------------- | ------------------------------ |
| **Python**       | Main programming language      |
| **Pandas**       | Data cleaning & transformation |
| **Boto3**        | Communication with AWS         |
| **AWS S3**       | Cloud data storage             |
| **PostgreSQL**   | Local database & testing       |
| **AWS Redshift** | Cloud Data Warehouse           |
| **SQL**          | Data analysis                  |
| **Power BI**     | Data visualization             |
| **Git & GitHub** | Version control                |

---

# 📁 Project Structure

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

Folder structure được chia theo từng responsibility để project dễ maintain và mở rộng hơn.

---

# 🔄 ETL Process

## 1. Extract

The pipeline starts by reading the raw CSV file containing e-commerce orders.

Raw data sau đó được upload lên **AWS S3** để lưu trữ riêng biệt với processed data.

```text
Local CSV
   ↓
Python
   ↓
AWS S3 / raw/
```

Việc giữ raw data riêng giúp có thể quay lại dữ liệu ban đầu nếu transformation xảy ra lỗi.

---

## 2. Transform

Data được xử lý bằng **Python + Pandas**.

Transformation process bao gồm:

* Removing duplicate records
* Handling missing values
* Checking data types
* Validating quantity
* Validating product price
* Checking discount values
* Standardizing categories
* Standardizing cities
* Validating order status
* Calculating total order amount

Total amount được tính theo công thức:

```text
total_amount =
quantity × unit_price × (1 - discount)
```

Sau khi transformation hoàn tất, processed dataset được upload lên:

```text
AWS S3 / processed/
```

---

## 3. Load

Processed data được load vào **PostgreSQL** để testing và thực hiện SQL analytics.

Đối với cloud environment, project có thể sử dụng **AWS Redshift** làm Data Warehouse.

```text
Processed CSV
     ↓
PostgreSQL
     ↓
SQL Analytics
```

Hoặc trong cloud:

```text
AWS S3
   ↓
AWS Redshift
   ↓
SQL Analytics
```

---

# 🏢 Data Warehouse

Project sử dụng một mô hình **Star Schema** đơn giản để phục vụ analytical queries.

```text
                  dim_customer
                       │
                       │
dim_product ──── fact_sales ──── dim_date
                       │
                       │
                 dim_location
```

## Fact Table

### `fact_sales`

Chứa các thông tin liên quan đến sales transaction:

* Quantity
* Unit price
* Discount
* Total amount
* Customer
* Product
* Date
* Location

## Dimension Tables

### `dim_customer`

Lưu thông tin liên quan đến customer.

### `dim_product`

Lưu product name, product ID và category.

### `dim_date`

Lưu thông tin về:

* Date
* Day
* Month
* Quarter
* Year

### `dim_location`

Lưu city và các thông tin location liên quan.

---

# 📈 SQL Analytics

Sau khi data được load vào database, SQL được sử dụng để answer các business questions.

Ví dụ:

* What is the total revenue?
* How does revenue change by month?
* Which products sell the most?
* Which categories generate the most revenue?
* Which cities have the highest sales?
* What is the average order value?
* Which customers generate the most revenue?
* Which payment methods are used most often?

Các query được lưu trong:

```text
sql/analytics.sql
```

Data quality queries được lưu trong:

```text
sql/data_quality.sql
```

---

# 📊 Power BI Dashboard

Processed data có thể được connect vào **Power BI** để tạo một sales dashboard.

Dashboard dự kiến gồm các phần:

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

Mục tiêu của dashboard là biến kết quả từ SQL analytics thành **visual business insights** dễ đọc hơn.

---

# 🧪 Data Quality

Data quality là một phần quan trọng của pipeline.

Trước khi data được load vào database, pipeline sẽ thực hiện một số checks:

```text
Duplicate order IDs
        ↓
Missing customer IDs
        ↓
Missing product IDs
        ↓
Invalid quantities
        ↓
Invalid prices
        ↓
Invalid discounts
        ↓
Invalid order status
        ↓
Invalid payment methods
```

Các records không hợp lệ sẽ được xử lý hoặc loại bỏ tùy theo từng loại lỗi.

Việc này giúp hạn chế **bad data** đi vào database và ảnh hưởng đến kết quả analytics.

---

# ⚙️ Running the Project

## 1. Clone Repository

```bash
git clone <repository-url>
cd cloud-data-pipeline
```

## 2. Create Virtual Environment

Trên Windows:

```powershell
python -m venv venv
```

Activate environment:

```powershell
venv\Scripts\activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Tạo file `.env`:

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

⚠️ **Do not upload `.env` to GitHub.**

File `.env` nên được thêm vào `.gitignore` để tránh accidentally expose credentials.

---

# ▶️ Generate Dataset

Chạy data generator:

```bash
python src/generate_data.py
```

Script sẽ tạo raw e-commerce dataset và lưu vào:

```text
data/raw/orders.csv
```

Sau đó pipeline có thể được chạy bằng:

```bash
python src/pipeline.py
```

Pipeline sẽ thực hiện các bước chính:

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

# 🖥️ Example Output

```text
====================================
CLOUD DATA ANALYTICS PIPELINE
====================================

[1] Data ingestion SUCCESS

[2] Upload raw data SUCCESS

[3] Data transformation SUCCESS

[4] Upload processed data SUCCESS

[5] Load database SUCCESS

[6] Data quality SUCCESS

Total records: 10000
Valid records: 9850
Invalid records: 150

Pipeline completed successfully.

====================================
```

Output thực tế có thể thay đổi tùy vào dataset và configuration.

---

# 🚀 Future Improvements

Project hiện tại mới tập trung vào basic pipeline nên vẫn còn khá nhiều thứ có thể improve.

Một số hướng phát triển tiếp theo:

* [ ] Add real-time data streaming
* [ ] Integrate Apache Kafka
* [ ] Use AWS Glue for ETL
* [ ] Move completely to AWS Redshift
* [ ] Add automated pipeline scheduling
* [ ] Improve data quality checks
* [ ] Add automated testing
* [ ] Add monitoring and alerting
* [ ] Improve Power BI dashboard
* [ ] Add sales forecasting using Machine Learning

Một số features có thể được triển khai sau khi core pipeline đã stable.

---

# 📚 What I Learned

Through this project, mình hiểu rõ hơn cách các components trong một data system kết nối với nhau.

Thay vì chỉ đọc và phân tích một CSV file, project này giúp mình thực hành toàn bộ flow:

```text
Raw Data
   ↓
Ingestion
   ↓
Storage
   ↓
ETL
   ↓
Database
   ↓
Data Warehouse
   ↓
SQL Analytics
   ↓
Visualization
```

Mình cũng hiểu rõ hơn sự khác nhau giữa **raw data, processed data, database, data warehouse, ETL và analytics**.

Quan trọng hơn, project giúp mình có cái nhìn thực tế hơn về cách một **Cloud Data Analytics Pipeline** có thể được xây dựng và phát triển từng bước.

---

# 👨‍💻 Author

**Huy**

This project was created for learning and practicing:

**Cloud Computing • Data Engineering • Data Analytics • SQL • Business Intelligence**

> This is a learning project. The e-commerce dataset is synthetic and does not contain real customer information.



project started : 25/7/2026
