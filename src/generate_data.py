"""
generate_data.py
================
Tạo dữ liệu đơn hàng e-commerce GIẢ LẬP và lưu vào  data/raw/orders.csv

File CSV này đóng vai trò "Data Source" (nguồn dữ liệu) của pipeline.
Ta CỐ TÌNH chèn dữ liệu "bẩn" để phần Data Cleaning có việc để làm:

    - dòng trùng lặp hoàn toàn (exact duplicate)
    - dòng trùng order_id nhưng nội dung khác
    - ô bị bỏ trống (missing)
    - giá trị sai (quantity <= 0, giá <= 0, discount > 1, ngày sai, ...)
    - chữ viết lộn xộn (hcm / HO CHI MINH / "  ha noi  ", electronics, completed, ...)

Chạy:
    python src/generate_data.py               # 10.000 dòng
    python src/generate_data.py --rows 20000  # số dòng tuỳ ý

Cùng một seed (42) sẽ luôn cho ra CÙNG một file -> kết quả dễ so sánh, dễ debug.
"""

import argparse
import calendar
import csv
import logging
import random
import sys
from datetime import date

import config

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# 1. THAM SỐ
# ------------------------------------------------------------------
NUM_ROWS = 10_000  # tổng số dòng trong file (đã gồm cả dòng bẩn)
RANDOM_SEED = 42
NUM_CUSTOMERS = 2_000
ORDER_YEAR = 2026
# Trọng số từng tháng (tháng 1..8): số càng lớn thì tháng đó càng nhiều đơn.
# Tháng 4 cố ý giảm nhẹ để câu truy vấn "tăng trưởng theo tháng" có cả tăng lẫn giảm.
MONTH_WEIGHTS = {1: 8, 2: 9, 3: 11, 4: 10, 5: 12, 6: 13, 7: 15, 8: 16}

# Tỉ lệ dữ liệu bẩn so với tổng số dòng. Với 10.000 dòng:
EXACT_DUPLICATE_RATIO = 0.015   # 150 dòng trùng hoàn toàn
SAME_ID_DUPLICATE_RATIO = 0.003  # 30 dòng trùng order_id nhưng khác nội dung
MISSING_RATIO = 0.03            # 300 dòng bị thiếu 1 ô
INVALID_RATIO = 0.025           # 250 dòng có giá trị sai
MESSY_TEXT_RATIO = 0.04         # 400 dòng viết hoa/thường lộn xộn (vẫn sửa được)

COLUMNS = [
    "order_id", "customer_id", "order_date", "product_id", "product_name",
    "category", "quantity", "unit_price", "discount", "payment_method",
    "city", "status",
]

# (product_id, product_name, category, unit_price VND)
PRODUCTS = [
    ("P001", "Laptop ASUS", "Electronics", 25_000_000),
    ("P002", "iPhone 15", "Electronics", 22_000_000),
    ("P003", "Samsung Galaxy S24", "Electronics", 18_000_000),
    ("P004", "Sony Headphones", "Electronics", 3_500_000),
    ("P005", "Men T-Shirt", "Fashion", 250_000),
    ("P006", "Women Dress", "Fashion", 650_000),
    ("P007", "Nike Sneakers", "Fashion", 2_500_000),
    ("P008", "Rice Cooker", "Home Appliances", 1_500_000),
    ("P009", "Air Fryer", "Home Appliances", 2_800_000),
    ("P010", "Vacuum Cleaner", "Home Appliances", 4_200_000),
    ("P011", "Python Programming Book", "Books", 300_000),
    ("P012", "Data Engineering Book", "Books", 450_000),
    ("P013", "Lipstick", "Beauty", 450_000),
    ("P014", "Yoga Mat", "Sports", 400_000),
    ("P015", "Badminton Racket", "Sports", 900_000),
]

# Thành phố và "độ phổ biến" tương đối của từng thành phố
CITIES = [
    "Ho Chi Minh", "Ha Noi", "Da Nang", "Can Tho", "Hai Phong",
    "Bien Hoa", "Thu Dau Mot", "Nha Trang", "Vung Tau", "Hue",
]
CITY_WEIGHTS = [30, 20, 10, 6, 6, 8, 8, 5, 4, 3]

# Cách viết "lộn xộn" thường gặp của một số thành phố
MESSY_CITY_ALIASES = {
    "Ho Chi Minh": ["hcm", "HCM", "Saigon"],
    "Ha Noi": ["hanoi", "HANOI"],
    "Da Nang": ["danang"],
}

PAYMENT_WEIGHTS = {"Banking": 35, "Credit Card": 25, "Cash": 20, "E-Wallet": 20}
STATUS_WEIGHTS = {"Completed": 80, "Pending": 6, "Cancelled": 9, "Returned": 5}
DISCOUNT_CHOICES = [0.0, 0.0, 0.05, 0.10, 0.15, 0.20]


# ------------------------------------------------------------------
# 2. TẠO DÒNG DỮ LIỆU HỢP LỆ
# ------------------------------------------------------------------
def random_order_date() -> date:
    """
    Chọn ngày ngẫu nhiên: trước hết chọn THÁNG theo MONTH_WEIGHTS (tháng sau đông hơn),
    rồi chọn 1 ngày bất kỳ trong tháng đó.
    """
    month = random.choices(list(MONTH_WEIGHTS), weights=list(MONTH_WEIGHTS.values()))[0]
    days_in_month = calendar.monthrange(ORDER_YEAR, month)[1]
    return date(ORDER_YEAR, month, random.randint(1, days_in_month))


def create_valid_order(order_number: int) -> dict:
    """Tạo 1 đơn hàng hợp lệ (dictionary: tên cột -> giá trị)."""
    product_id, product_name, category, unit_price = random.choice(PRODUCTS)

    return {
        "order_id": f"ORD{order_number:06d}",                       # ORD000001
        "customer_id": f"CUS{random.randint(1, NUM_CUSTOMERS):05d}",  # CUS00001
        "order_date": random_order_date().isoformat(),               # 2026-01-15
        "product_id": product_id,
        "product_name": product_name,
        "category": category,
        "quantity": random.choices([1, 2, 3, 4, 5], weights=[50, 25, 12, 8, 5])[0],
        "unit_price": unit_price,
        "discount": f"{random.choice(DISCOUNT_CHOICES):.2f}",        # 0.10
        "payment_method": random.choices(
            list(PAYMENT_WEIGHTS), weights=list(PAYMENT_WEIGHTS.values())
        )[0],
        "city": random.choices(CITIES, weights=CITY_WEIGHTS)[0],
        "status": random.choices(
            list(STATUS_WEIGHTS), weights=list(STATUS_WEIGHTS.values())
        )[0],
    }


# ------------------------------------------------------------------
# 3. LÀM "BẨN" DỮ LIỆU (mỗi hàm sửa trực tiếp 1 dòng)
# ------------------------------------------------------------------
def make_missing(row: dict) -> None:
    """Xoá trống 1 ô ngẫu nhiên (giống dữ liệu bị thiếu ngoài đời thật)."""
    column = random.choice([
        "customer_id", "product_id", "product_name", "category",
        "discount", "payment_method", "city", "status",
    ])
    row[column] = ""


def make_invalid(row: dict) -> None:
    """Gán 1 giá trị SAI cho dòng (không thể sửa được, phải loại bỏ)."""
    problem = random.choice([
        "quantity_not_positive", "quantity_text", "price_not_positive",
        "discount_too_high", "discount_negative", "bad_date",
        "bad_status", "bad_payment",
    ])
    if problem == "quantity_not_positive":
        row["quantity"] = random.choice([0, -1, -5])
    elif problem == "quantity_text":
        row["quantity"] = "abc"
    elif problem == "price_not_positive":
        row["unit_price"] = random.choice([0, -100_000])
    elif problem == "discount_too_high":
        row["discount"] = random.choice(["1.50", "2.00"])
    elif problem == "discount_negative":
        row["discount"] = "-0.20"
    elif problem == "bad_date":
        row["order_date"] = random.choice(["2026-13-45", "15/01/2026", "not a date"])
    elif problem == "bad_status":
        row["status"] = "Invalid_Status"
    elif problem == "bad_payment":
        row["payment_method"] = "Bitcoin"


def make_messy(row: dict) -> None:
    """Viết hoa/thường/khoảng trắng lộn xộn - dữ liệu vẫn SỬA ĐƯỢC ở bước transform."""
    field = random.choice(["city", "city", "category", "status"])
    if field == "city":
        city = row["city"]
        variants = [city.lower(), city.upper(), f"  {city}  "]
        variants += MESSY_CITY_ALIASES.get(city, [])
        row["city"] = random.choice(variants)
    elif field == "category":
        row["category"] = random.choice([row["category"].lower(), row["category"].upper()])
    else:
        row["status"] = row["status"].lower()


# ------------------------------------------------------------------
# 4. TẠO TOÀN BỘ DATASET
# ------------------------------------------------------------------
def generate_orders(num_rows: int = NUM_ROWS, seed: int = RANDOM_SEED) -> list:
    """Trả về list gồm num_rows dòng (mỗi dòng là 1 dict), có cả dữ liệu bẩn."""
    random.seed(seed)

    num_exact_duplicates = int(num_rows * EXACT_DUPLICATE_RATIO)
    num_same_id_duplicates = int(num_rows * SAME_ID_DUPLICATE_RATIO)
    num_missing = int(num_rows * MISSING_RATIO)
    num_invalid = int(num_rows * INVALID_RATIO)
    num_messy = int(num_rows * MESSY_TEXT_RATIO)

    # Bước 1: tạo các đơn hợp lệ (chừa chỗ cho các dòng trùng lặp thêm vào sau)
    num_base = num_rows - num_exact_duplicates - num_same_id_duplicates
    rows = [create_valid_order(number) for number in range(1, num_base + 1)]

    # Bước 2: chọn NGẪU NHIÊN các dòng để làm bẩn (mỗi dòng chỉ bị 1 loại lỗi)
    picked = random.sample(range(num_base), num_missing + num_invalid + num_messy)
    missing_indexes = picked[:num_missing]
    invalid_indexes = picked[num_missing:num_missing + num_invalid]
    messy_indexes = picked[num_missing + num_invalid:]

    for index in missing_indexes:
        make_missing(rows[index])
    for index in invalid_indexes:
        make_invalid(rows[index])
    for index in messy_indexes:
        make_messy(rows[index])

    # Bước 3: thêm các dòng trùng lặp vào CUỐI file (giống dữ liệu bị gửi lại 2 lần)
    for index in random.sample(range(num_base), num_exact_duplicates):
        rows.append(dict(rows[index]))  # bản sao y hệt

    for index in random.sample(range(num_base), num_same_id_duplicates):
        copy = dict(rows[index])
        copy["quantity"] = random.randint(6, 9)  # cùng order_id nhưng khác số lượng
        rows.append(copy)

    return rows


def save_orders_to_csv(rows: list, path) -> None:
    """Ghi list dict ra file CSV (UTF-8, có dòng tiêu đề)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def run_generate(num_rows: int = NUM_ROWS) -> dict:
    """Tạo dữ liệu và lưu vào config.RAW_DATA_PATH. Trả về thông tin tóm tắt."""
    logger.info("Generating %d rows of sample e-commerce data...", num_rows)
    rows = generate_orders(num_rows)
    save_orders_to_csv(rows, config.RAW_DATA_PATH)
    logger.info("Saved %d rows to %s", len(rows), config.RAW_DATA_PATH)
    return {"rows": len(rows), "path": str(config.RAW_DATA_PATH)}


def main() -> int:
    """Hàm chạy khi gõ: python src/generate_data.py"""
    config.setup_logging()

    parser = argparse.ArgumentParser(description="Generate sample e-commerce orders CSV.")
    parser.add_argument("--rows", type=int, default=NUM_ROWS, help="so dong can tao (mac dinh 10000)")
    args = parser.parse_args()

    try:
        run_generate(args.rows)
        return 0
    except Exception as error:  # noqa: BLE001 - bắt mọi lỗi để in thông báo dễ hiểu
        logger.error("Could not generate data: %s", error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
