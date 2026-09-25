"""
config.py
=========
Nơi TẬP TRUNG mọi cấu hình của project. Các file khác chỉ cần viết:

    import config
    config.S3_BUCKET_NAME

Vì sao cần file này?
- Không phải sửa nhiều file khi đổi đường dẫn / tên bucket / thông tin database.
- Bí mật (key AWS, mật khẩu DB) KHÔNG nằm trong code mà nằm trong file .env
  (file .env không được commit lên GitHub).
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL


# 1. ĐƯỜNG DẪN (dùng pathlib để chạy được cả Windows lẫn Linux/Mac)

# __file__ = .../cloud-data-pipeline/src/config.py
# parent   = .../src            parent.parent = .../cloud-data-pipeline
BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DATA_PATH = BASE_DIR / "data" / "raw" / "orders.csv"
PROCESSED_DATA_PATH = BASE_DIR / "data" / "processed" / "orders_clean.csv"
REJECTED_DATA_PATH = BASE_DIR / "data" / "processed" / "orders_rejected.csv"
DATA_QUALITY_REPORT_PATH = BASE_DIR / "data" / "processed" / "data_quality_report.csv"

SQL_DIR = BASE_DIR / "sql"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "pipeline.log"


# 2. ĐỌC FILE .env

# load_dotenv đọc từng dòng KEY=VALUE trong .env và nạp vào biến môi trường.
# boto3 sẽ TỰ ĐỘNG dùng AWS_ACCESS_KEY_ID và AWS_SECRET_ACCESS_KEY từ biến môi trường,
# nên trong code ta không cần (và không được) viết key ra.
load_dotenv(BASE_DIR / ".env")

# ---------- AWS ----------
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")

# "Đường dẫn" bên trong bucket. S3 không có thư mục thật, "raw/" chỉ là tiền tố (prefix)
# của tên file, nhưng giao diện AWS hiển thị nó như một thư mục.
S3_RAW_KEY = "raw/orders.csv"
S3_PROCESSED_KEY = "processed/orders_clean.csv"

# ---------- PostgreSQL ----------
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "ecommerce_analytics")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")


# 3. QUY TẮC NGHIỆP VỤ (dùng chung cho generate_data, transform, test)

# Nếu sửa 2 danh sách này, nhớ sửa luôn trong sql/data_quality.sql.
VALID_STATUSES = ["Completed", "Pending", "Cancelled", "Returned"]
VALID_PAYMENT_METHODS = ["Banking", "Credit Card", "Cash", "E-Wallet"]

# Tên thành phố viết tắt / viết sai phổ biến -> tên chuẩn
# (đã được đưa về dạng "Title Case" trước khi tra bảng này)
CITY_ALIASES = {
    "Hcm": "Ho Chi Minh",
    "Hcmc": "Ho Chi Minh",
    "Saigon": "Ho Chi Minh",
    "Sai Gon": "Ho Chi Minh",
    "Hanoi": "Ha Noi",
    "Danang": "Da Nang",
}



# 4. HÀM TIỆN ÍCH

def get_s3_bucket() -> str:
    """Trả về tên bucket; báo lỗi dễ hiểu nếu bạn chưa điền vào .env."""
    if not S3_BUCKET_NAME or S3_BUCKET_NAME.startswith("cloud-data-pipeline-yourname"):
        raise ValueError(
            "S3_BUCKET_NAME chua duoc cau hinh. Mo file .env va dien ten bucket that "
            "cua ban (xem docs/AWS_SETUP.md). Neu chua co AWS, chay: python src/pipeline.py --skip-s3"
        )
    return S3_BUCKET_NAME


def get_database_url() -> URL:
    """
    Tạo địa chỉ kết nối PostgreSQL:
        postgresql+psycopg2://user:password@host:port/database

    Dùng URL.create thay vì tự ghép chuỗi để mật khẩu chứa ký tự đặc biệt
    (@, #, /, ...) vẫn hoạt động đúng.
    """
    return URL.create(
        drivername="postgresql+psycopg2",
        username=DB_USER,
        password=DB_PASSWORD or None,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    )


def setup_logging() -> None:
    """
    Cấu hình logging: ghi ĐỒNG THỜI ra màn hình và ra file logs/pipeline.log.
    Ví dụ một dòng log:
        2026-09-23 10:00:01 INFO Starting pipeline
    Gọi nhiều lần cũng an toàn (không bị ghi trùng dòng).
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    if root_logger.handlers:  # đã cấu hình rồi thì thôi
        return

    root_logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # boto3 mặc định in rất nhiều log kỹ thuật, ta chỉ giữ cảnh báo/lỗi.
    for noisy_library in ("boto3", "botocore", "s3transfer", "urllib3"):
        logging.getLogger(noisy_library).setLevel(logging.WARNING)
