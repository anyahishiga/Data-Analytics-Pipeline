"""
transform.py
============
Bước ETL bằng Python + Pandas: đọc dữ liệu RAW -> làm sạch -> biến đổi -> lưu PROCESSED.

    s3://bucket/raw/orders.csv                 (hoặc data/raw/orders.csv nếu --skip-s3)
        │
        ▼  1. clean_text              cắt khoảng trắng, ô rỗng -> thiếu (NaN)
        ▼  2. remove_duplicates       bỏ dòng trùng
        ▼  3. handle_missing_values   thiếu cột bắt buộc -> loại; cột phụ -> điền giá trị
        ▼  4. validate_data_types     ngày / số phải đúng định dạng
        ▼  5. validate_quantity       quantity phải là số nguyên > 0
        ▼  6. validate_price          unit_price phải > 0
        ▼  7. validate_discount       0 <= discount <= 1
        ▼  8. validate_status_and_payment   chỉ nhận giá trị hợp lệ
        ▼  9. add_total_amount        total_amount = quantity * unit_price * (1 - discount)
        ▼ 10. normalize_city          "  ha noi " / "HANOI" -> "Ha Noi"
        ▼ 11. normalize_category      "electronics" -> "Electronics"
    data/processed/orders_clean.csv   ──►  s3://bucket/processed/orders_clean.csv

Dòng bị loại không bị xoá mất: chúng được ghi vào  data/processed/orders_rejected.csv
kèm cột reject_reason để bạn biết VÌ SAO chúng bị loại.

Chạy riêng bước này:
    python src/transform.py               # đọc raw từ S3, upload processed lên S3
    python src/transform.py --skip-s3     # chỉ dùng file trên máy (chưa cần AWS)
"""

import argparse
import logging
import sys

import pandas as pd

import config
from ingest import read_csv_from_s3, upload_to_s3

logger = logging.getLogger(__name__)

EXPECTED_COLUMNS = [
    "order_id", "customer_id", "order_date", "product_id", "product_name",
    "category", "quantity", "unit_price", "discount", "payment_method",
    "city", "status",
]
FINAL_COLUMNS = EXPECTED_COLUMNS + ["total_amount"]

# Thiếu 1 trong các cột này thì dòng vô nghĩa -> loại bỏ.
REQUIRED_COLUMNS = [
    "order_id", "customer_id", "order_date", "product_id",
    "quantity", "unit_price", "payment_method", "status",
]


# ------------------------------------------------------------------
# HÀM HỖ TRỢ
# ------------------------------------------------------------------
def split_invalid(df: pd.DataFrame, is_invalid: pd.Series, reason: str):
    """
    Tách các dòng không hợp lệ ra khỏi DataFrame.

    Trả về 2 DataFrame:
        (các dòng hợp lệ, các dòng bị loại kèm cột reject_reason)
    """
    rejected = df[is_invalid].copy()
    rejected["reject_reason"] = reason
    valid = df[~is_invalid].copy()
    return valid, rejected


def combine_rejected(parts: list) -> pd.DataFrame:
    """Gộp nhiều DataFrame 'bị loại' thành một (bỏ qua các phần rỗng)."""
    parts = [part for part in parts if not part.empty]
    if not parts:
        return pd.DataFrame(columns=EXPECTED_COLUMNS + ["reject_reason"])

    combined = pd.concat(parts, ignore_index=True)
    # Các dòng bị loại ở bước sau đã được đổi order_date sang kiểu ngày (Timestamp);
    # đổi lại thành chữ "YYYY-MM-DD" cho file orders_rejected.csv dễ đọc.
    combined["order_date"] = combined["order_date"].apply(
        lambda value: value.strftime("%Y-%m-%d") if isinstance(value, pd.Timestamp) else value
    )
    return combined


def check_columns(df: pd.DataFrame) -> None:
    """Đảm bảo file raw có đủ 12 cột cần thiết."""
    missing = [column for column in EXPECTED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"File raw thieu cac cot: {missing}")


# ------------------------------------------------------------------
# CÁC BƯỚC BIẾN ĐỔI (mỗi hàm làm đúng 1 việc)
# ------------------------------------------------------------------
def clean_text(df: pd.DataFrame) -> pd.DataFrame:
    """Cắt khoảng trắng đầu/cuối mọi ô; ô chỉ chứa khoảng trắng coi như thiếu (NaN)."""
    df = df.copy()
    for column in df.columns:
        stripped = df[column].str.strip()
        df[column] = stripped.mask(stripped == "")
    return df


def remove_duplicates(df: pd.DataFrame):
    """
    Bỏ dòng trùng. Trả về (DataFrame, số dòng đã bỏ).
        - Trùng hoàn toàn mọi cột            -> giữ 1 bản
        - Trùng order_id nhưng khác nội dung -> giữ dòng XUẤT HIỆN ĐẦU TIÊN
    """
    rows_before = len(df)
    df = df.drop_duplicates()
    df = df.drop_duplicates(subset="order_id", keep="first")
    return df.copy(), rows_before - len(df)


def handle_missing_values(df: pd.DataFrame):
    """
    Xử lý ô thiếu. Trả về (DataFrame, DataFrame bị loại).
        - Thiếu cột BẮT BUỘC (id, ngày, số lượng, giá, thanh toán, trạng thái) -> loại dòng
        - discount thiếu   -> điền 0 (không giảm giá)
        - product_name / category thiếu -> lấy từ các dòng khác có cùng product_id
        - city / product_name / category vẫn thiếu -> điền "Unknown"
    """
    is_missing_required = df[REQUIRED_COLUMNS].isna().any(axis=1)
    df, rejected = split_invalid(df, is_missing_required, "missing_required_value")

    df["discount"] = df["discount"].fillna("0")

    # "Danh mục sản phẩm" được suy ra từ chính dữ liệu: mỗi product_id -> 1 tên, 1 category
    for column in ["product_name", "category"]:
        catalog = (
            df.dropna(subset=[column])
            .drop_duplicates(subset="product_id")
            .set_index("product_id")[column]
        )
        df[column] = df[column].fillna(df["product_id"].map(catalog))

    for column in ["product_name", "category", "city"]:
        df[column] = df[column].fillna("Unknown")

    return df, rejected


def validate_data_types(df: pd.DataFrame):
    """
    Kiểm tra ngày và số có đúng định dạng không, rồi ĐỔI KIỂU dữ liệu.
    Ví dụ order_date = "2026-13-45" hoặc quantity = "abc" -> bị loại.
    """
    rejected_parts = []

    # errors="coerce": giá trị không đổi được sẽ thành NaT/NaN thay vì báo lỗi
    bad_dates = pd.to_datetime(df["order_date"], format="%Y-%m-%d", errors="coerce").isna()
    df, rejected = split_invalid(df, bad_dates, "invalid_order_date")
    rejected_parts.append(rejected)

    for column, reason in [
        ("quantity", "invalid_quantity_type"),
        ("unit_price", "invalid_price_type"),
        ("discount", "invalid_discount_type"),
    ]:
        is_bad = pd.to_numeric(df[column], errors="coerce").isna()
        df, rejected = split_invalid(df, is_bad, reason)
        rejected_parts.append(rejected)

    # Tới đây mọi giá trị đều đổi được -> đổi kiểu thật sự
    df["order_date"] = pd.to_datetime(df["order_date"], format="%Y-%m-%d")
    df["quantity"] = pd.to_numeric(df["quantity"])
    df["unit_price"] = pd.to_numeric(df["unit_price"])
    df["discount"] = pd.to_numeric(df["discount"])

    return df, combine_rejected(rejected_parts)


def validate_quantity(df: pd.DataFrame):
    """quantity phải là số nguyên dương (1, 2, 3, ...)."""
    is_bad = (df["quantity"] <= 0) | (df["quantity"] % 1 != 0)
    df, rejected = split_invalid(df, is_bad, "invalid_quantity")
    df["quantity"] = df["quantity"].astype(int)
    return df, rejected


def validate_price(df: pd.DataFrame):
    """unit_price phải lớn hơn 0."""
    is_bad = df["unit_price"] <= 0
    return split_invalid(df, is_bad, "invalid_unit_price")


def validate_discount(df: pd.DataFrame):
    """discount là tỉ lệ giảm giá, phải nằm trong khoảng 0..1 (0.10 = giảm 10 phần trăm)."""
    is_bad = (df["discount"] < 0) | (df["discount"] > 1)
    return split_invalid(df, is_bad, "invalid_discount")


def validate_status_and_payment(df: pd.DataFrame):
    """Chuẩn hoá chữ (completed -> Completed) rồi chỉ giữ giá trị nằm trong danh sách hợp lệ."""
    df = df.copy()
    df["status"] = df["status"].str.title()
    df["payment_method"] = df["payment_method"].str.title()

    rejected_parts = []
    is_bad_status = ~df["status"].isin(config.VALID_STATUSES)
    df, rejected = split_invalid(df, is_bad_status, "invalid_status")
    rejected_parts.append(rejected)

    is_bad_payment = ~df["payment_method"].isin(config.VALID_PAYMENT_METHODS)
    df, rejected = split_invalid(df, is_bad_payment, "invalid_payment_method")
    rejected_parts.append(rejected)

    return df, combine_rejected(rejected_parts)


def add_total_amount(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tạo cột total_amount = quantity * unit_price * (1 - discount)
    Ví dụ: 2 * 10.000.000 * (1 - 0.1) = 18.000.000
    """
    df = df.copy()
    df["total_amount"] = (df["quantity"] * df["unit_price"] * (1 - df["discount"])).round(2)
    return df


def normalize_city(df: pd.DataFrame) -> pd.DataFrame:
    """'  ha   noi ' / 'HANOI' / 'hcm'  ->  'Ha Noi' / 'Ha Noi' / 'Ho Chi Minh'."""
    df = df.copy()
    city = df["city"].str.replace(r"\s+", " ", regex=True).str.strip().str.title()
    df["city"] = city.replace(config.CITY_ALIASES)
    return df


def normalize_category(df: pd.DataFrame) -> pd.DataFrame:
    """'electronics' / 'ELECTRONICS'  ->  'Electronics'."""
    df = df.copy()
    df["category"] = df["category"].str.strip().str.title()
    return df


# ------------------------------------------------------------------
# GHÉP CÁC BƯỚC LẠI THÀNH MỘT PIPELINE
# ------------------------------------------------------------------
def transform_data(raw_df: pd.DataFrame):
    """
    Nhận DataFrame raw, trả về:
        clean_df    : dữ liệu sạch (có thêm cột total_amount)
        rejected_df : các dòng bị loại + lý do
        stats       : dict số liệu thống kê
    """
    check_columns(raw_df)
    rejected_parts = []

    df = clean_text(raw_df[EXPECTED_COLUMNS])
    df, duplicates_removed = remove_duplicates(df)

    df, rejected = handle_missing_values(df)
    rejected_parts.append(rejected)

    df, rejected = validate_data_types(df)
    rejected_parts.append(rejected)

    df, rejected = validate_quantity(df)
    rejected_parts.append(rejected)

    df, rejected = validate_price(df)
    rejected_parts.append(rejected)

    df, rejected = validate_discount(df)
    rejected_parts.append(rejected)

    df, rejected = validate_status_and_payment(df)
    rejected_parts.append(rejected)

    df = add_total_amount(df)
    df = normalize_city(df)
    df = normalize_category(df)

    clean_df = df[FINAL_COLUMNS].sort_values("order_id").reset_index(drop=True)
    rejected_df = combine_rejected(rejected_parts)

    stats = {
        "rows_read": len(raw_df),
        "duplicates_removed": duplicates_removed,
        "rows_rejected": len(rejected_df),
        "rows_clean": len(clean_df),
    }
    return clean_df, rejected_df, stats


# ------------------------------------------------------------------
# ĐỌC / GHI FILE
# ------------------------------------------------------------------
def read_raw_data(use_s3: bool = True) -> pd.DataFrame:
    """Đọc dữ liệu raw từ S3 (mặc định) hoặc từ file trên máy."""
    if use_s3:
        bucket_name = config.get_s3_bucket()
        logger.info("Reading raw data from s3://%s/%s", bucket_name, config.S3_RAW_KEY)
        return read_csv_from_s3(bucket_name, config.S3_RAW_KEY)

    if not config.RAW_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Khong tim thay {config.RAW_DATA_PATH}. Hay chay:  python src/generate_data.py"
        )
    logger.info("Reading raw data from local file %s", config.RAW_DATA_PATH)
    return pd.read_csv(config.RAW_DATA_PATH, dtype=str, encoding="utf-8")


def save_processed_data(clean_df: pd.DataFrame, rejected_df: pd.DataFrame) -> None:
    """Lưu dữ liệu sạch và dữ liệu bị loại ra data/processed/."""
    config.PROCESSED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(
        config.PROCESSED_DATA_PATH, index=False, encoding="utf-8", date_format="%Y-%m-%d"
    )
    rejected_df.to_csv(config.REJECTED_DATA_PATH, index=False, encoding="utf-8")


def run_transform(use_s3: bool = True) -> dict:
    """Đọc raw -> transform -> lưu processed ra máy. Trả về dict thống kê."""
    logger.info("Starting transformation...")

    raw_df = read_raw_data(use_s3)
    logger.info("Read %d raw rows", len(raw_df))

    clean_df, rejected_df, stats = transform_data(raw_df)

    logger.info("Duplicates removed: %d", stats["duplicates_removed"])
    if stats["rows_rejected"] > 0:
        for reason, count in rejected_df["reject_reason"].value_counts().items():
            logger.warning("Rejected %d rows: %s", count, reason)

    save_processed_data(clean_df, rejected_df)
    logger.info("Transformation completed: %d clean rows saved to %s",
                stats["rows_clean"], config.PROCESSED_DATA_PATH)
    return stats


def upload_processed_data() -> str:
    """Upload orders_clean.csv lên s3://bucket/processed/orders_clean.csv"""
    bucket_name = config.get_s3_bucket()
    logger.info("Uploading processed data to S3...")
    s3_uri = upload_to_s3(config.PROCESSED_DATA_PATH, bucket_name, config.S3_PROCESSED_KEY)
    logger.info("Upload successful. File is at %s", s3_uri)
    return s3_uri


def main() -> int:
    """Hàm chạy khi gõ: python src/transform.py [--skip-s3]"""
    config.setup_logging()

    parser = argparse.ArgumentParser(description="Clean and transform raw orders.")
    parser.add_argument("--skip-s3", action="store_true", help="dung file tren may, khong dung AWS S3")
    args = parser.parse_args()
    use_s3 = not args.skip_s3

    try:
        run_transform(use_s3)
        if use_s3:
            upload_processed_data()
        return 0
    except Exception as error:  # noqa: BLE001
        logger.error("Transformation failed: %s", error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
