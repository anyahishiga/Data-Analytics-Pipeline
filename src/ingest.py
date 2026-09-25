"""
ingest.py
=========
Bước INGESTION: đưa file CSV "thô" (raw) từ máy của bạn lên AWS S3 (Data Lake).

    data/raw/orders.csv  ──►  s3://<bucket>/raw/orders.csv

File này cũng chứa các hàm nói chuyện với S3 mà các file khác dùng lại:
    get_s3_client()    tạo "khách hàng" S3 của boto3
    upload_to_s3()     upload 1 file lên S3
    read_csv_from_s3() đọc 1 file CSV trên S3 thành DataFrame (dùng trong transform.py)

Chạy riêng bước này:
    python src/ingest.py
"""

import io
import logging
import sys
from pathlib import Path

import boto3
import pandas as pd
from botocore.exceptions import BotoCoreError, ClientError
from boto3.exceptions import S3UploadFailedError

import config

logger = logging.getLogger(__name__)


def get_s3_client():
    """
    Tạo S3 client. boto3 tự lấy AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
    từ biến môi trường (config.py đã nạp chúng từ file .env).
    """
    return boto3.client("s3", region_name=config.AWS_REGION)


def explain_aws_error(error: Exception) -> str:
    """Đổi lỗi kỹ thuật của AWS thành lời khuyên dễ hiểu cho người mới."""
    text = str(error)
    if "NoCredentialsError" in type(error).__name__ or "Unable to locate credentials" in text:
        return "Khong tim thay AWS key. Kiem tra AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY trong file .env."
    if "InvalidAccessKeyId" in text:
        return "AWS_ACCESS_KEY_ID sai hoac da bi xoa. Tao access key moi trong IAM."
    if "SignatureDoesNotMatch" in text:
        return "AWS_SECRET_ACCESS_KEY sai (thuong do copy thieu/thua ky tu)."
    if "NoSuchBucket" in text:
        return "Bucket khong ton tai. Kiem tra S3_BUCKET_NAME va AWS_REGION trong .env."
    if "AccessDenied" in text or "403" in text:
        return "IAM user khong co quyen tren bucket nay. Kiem tra policy (xem docs/AWS_SETUP.md)."
    if "NoSuchKey" in text or "404" in text:
        return "Khong tim thay file tren S3. Hay chay buoc upload raw truoc (python src/ingest.py)."
    if "EndpointConnectionError" in type(error).__name__ or "Could not connect" in text:
        return "Khong ket noi duoc AWS. Kiem tra Internet va AWS_REGION."
    return "Loi AWS khong xac dinh, xem chi tiet o tren."


def upload_to_s3(local_path, bucket_name: str, s3_key: str) -> str:
    """
    Upload 1 file lên S3.

    Tham số:
        local_path  : đường dẫn file trên máy, ví dụ data/raw/orders.csv
        bucket_name : tên bucket, ví dụ cloud-data-pipeline-yourname-2026
        s3_key      : tên/đường dẫn file TRONG bucket, ví dụ raw/orders.csv

    Trả về địa chỉ S3, ví dụ  s3://cloud-data-pipeline-yourname-2026/raw/orders.csv
    Nếu lỗi: ném exception với thông báo dễ hiểu (không im lặng nuốt lỗi).
    """
    local_path = Path(local_path)

    if not local_path.exists():
        raise FileNotFoundError(f"Khong tim thay file: {local_path}")
    if not bucket_name:
        raise ValueError("Ten bucket dang rong. Hay dien S3_BUCKET_NAME trong .env")

    try:
        s3_client = get_s3_client()
        s3_client.upload_file(str(local_path), bucket_name, s3_key)
    except (BotoCoreError, ClientError, S3UploadFailedError) as error:
        raise RuntimeError(f"Upload to S3 failed: {explain_aws_error(error)} | Chi tiet: {error}") from error

    return f"s3://{bucket_name}/{s3_key}"


def read_csv_from_s3(bucket_name: str, s3_key: str) -> pd.DataFrame:
    """
    Đọc thẳng 1 file CSV trên S3 vào DataFrame (không cần lưu ra ổ đĩa).
    Mọi cột được đọc dưới dạng chữ (dtype=str); việc đổi kiểu số/ngày do transform.py làm.
    """
    try:
        s3_client = get_s3_client()
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        content = response["Body"].read()  # toàn bộ file dưới dạng bytes
    except (BotoCoreError, ClientError) as error:
        raise RuntimeError(f"Read from S3 failed: {explain_aws_error(error)} | Chi tiet: {error}") from error

    return pd.read_csv(io.BytesIO(content), dtype=str, encoding="utf-8")


def run_ingestion() -> dict:
    """Thực hiện toàn bộ bước ingestion. Ném exception nếu có lỗi."""
    logger.info("Starting ingestion...")

    bucket_name = config.get_s3_bucket()

    if not config.RAW_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Khong tim thay {config.RAW_DATA_PATH}. Hay chay:  python src/generate_data.py"
        )

    logger.info("Reading CSV...")
    df = pd.read_csv(config.RAW_DATA_PATH, dtype=str)
    logger.info("CSV has %d rows and %d columns", len(df), len(df.columns))

    logger.info("Uploading to S3...")
    s3_uri = upload_to_s3(config.RAW_DATA_PATH, bucket_name, config.S3_RAW_KEY)

    logger.info("Upload successful. File is at %s", s3_uri)
    return {"rows": len(df), "s3_uri": s3_uri}


def main() -> int:
    """Hàm chạy khi gõ: python src/ingest.py   (trả về 0 nếu OK, 1 nếu lỗi)"""
    config.setup_logging()
    try:
        run_ingestion()
        return 0
    except Exception as error:  # noqa: BLE001
        logger.error("Ingestion failed: %s", error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
