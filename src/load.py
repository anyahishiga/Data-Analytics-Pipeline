"""
load.py
=======
Bước LOAD: nạp dữ liệu đã làm sạch vào PostgreSQL.

    data/processed/orders_clean.csv
        │  (pandas đọc, SQLAlchemy ghi)
        ▼
    PostgreSQL:  bảng "orders"  ──►  Star Schema (dim_* + fact_sales)

Các bước bên trong run_load():
    1. Kết nối database (thông tin lấy từ .env)
    2. Chạy sql/create_tables.sql  (tạo bảng nếu chưa có)
    3. Xoá dữ liệu cũ trong "orders" rồi chèn dữ liệu mới (cùng 1 giao dịch)
    4. Chạy sql/build_star_schema.sql (đổ sang Star Schema)

Chạy riêng bước này:
    python src/load.py

Điều kiện: PostgreSQL đang chạy và database ecommerce_analytics đã được tạo
(xem docs/POSTGRESQL_SETUP.md).
"""

import logging
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

import config

logger = logging.getLogger(__name__)


def get_engine() -> Engine:
    """Tạo 'engine' - đối tượng SQLAlchemy quản lý kết nối tới database."""
    return create_engine(config.get_database_url())


def explain_db_error(error: Exception) -> str:
    """Đổi lỗi kỹ thuật của PostgreSQL thành lời khuyên dễ hiểu."""
    message = str(error).lower()
    if "password authentication failed" in message:
        return "Sai mat khau hoac user. Kiem tra DB_USER / DB_PASSWORD trong file .env."
    if "database" in message and "does not exist" in message:
        return (f"Database '{config.DB_NAME}' chua ton tai. Tao no bang pgAdmin hoac lenh: "
                f"CREATE DATABASE {config.DB_NAME};  (xem docs/POSTGRESQL_SETUP.md)")
    if "connection refused" in message or "could not connect" in message or "timeout" in message:
        return (f"Khong ket noi duoc toi {config.DB_HOST}:{config.DB_PORT}. "
                "PostgreSQL chua chay? Kiem tra service 'postgresql' trong Windows Services, "
                "va DB_HOST / DB_PORT trong .env.")
    if "could not translate host name" in message or "name or service not known" in message:
        return "DB_HOST sai (khong tim thay may chu). Voi PostgreSQL tren may minh hay dung DB_HOST=localhost."
    return "Loi database khong xac dinh, xem chi tiet ben duoi."


def check_connection(engine: Engine) -> None:
    """Thử chạy 'SELECT 1' để chắc chắn kết nối được. Nếu lỗi: ném RuntimeError dễ hiểu."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise RuntimeError(f"Cannot connect to PostgreSQL: {explain_db_error(error)} | Chi tiet: {error}") from error


def run_sql_file(engine: Engine, sql_path: Path) -> None:
    """Đọc 1 file .sql và chạy toàn bộ trong 1 giao dịch (lỗi giữa chừng thì hoàn tác hết)."""
    sql = Path(sql_path).read_text(encoding="utf-8")
    with engine.begin() as connection:  # begin() = tự COMMIT khi xong, tự ROLLBACK khi lỗi
        connection.exec_driver_sql(sql)


def create_tables(engine: Engine) -> None:
    """Tạo các bảng (orders + star schema) nếu chưa tồn tại."""
    logger.info("Creating tables (if not exist)...")
    run_sql_file(engine, config.SQL_DIR / "create_tables.sql")


def read_processed_csv() -> pd.DataFrame:
    """Đọc data/processed/orders_clean.csv."""
    if not config.PROCESSED_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Khong tim thay {config.PROCESSED_DATA_PATH}. Hay chay buoc transform truoc: "
            "python src/transform.py --skip-s3"
        )
    df = pd.read_csv(config.PROCESSED_DATA_PATH, parse_dates=["order_date"], encoding="utf-8")
    df["order_date"] = df["order_date"].dt.date  # DATE (không có giờ) cho khớp cột DATE trong DB
    return df


def insert_orders(engine: Engine, df: pd.DataFrame) -> int:
    """
    Xoá dữ liệu cũ rồi chèn toàn bộ df vào bảng orders (full refresh).
    Việc xoá và chèn nằm trong CÙNG 1 giao dịch: lỗi giữa chừng thì dữ liệu cũ vẫn còn nguyên.
    Trả về số dòng thực sự có trong bảng sau khi chèn.
    """
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE orders"))
        df.to_sql(
            "orders",
            con=connection,
            if_exists="append",  # thêm vào bảng có sẵn, KHÔNG tạo lại bảng
            index=False,
            method="multi",      # gộp nhiều dòng vào 1 câu INSERT cho nhanh
            chunksize=1000,
        )
        rows_in_table = connection.execute(text("SELECT COUNT(*) FROM orders")).scalar()
    return int(rows_in_table)


def build_star_schema(engine: Engine) -> dict:
    """Đổ dữ liệu sang star schema và trả về số dòng của từng bảng."""
    logger.info("Building star schema...")
    run_sql_file(engine, config.SQL_DIR / "build_star_schema.sql")

    counts = {}
    with engine.connect() as connection:
        for table in ["dim_customer", "dim_product", "dim_date", "dim_location", "fact_sales"]:
            counts[table] = int(connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar())
    return counts


def run_load() -> dict:
    """Thực hiện toàn bộ bước load. Ném exception nếu có lỗi."""
    logger.info("Loading database...")

    engine = get_engine()
    try:
        logger.info("Connecting to PostgreSQL at %s:%s/%s", config.DB_HOST, config.DB_PORT, config.DB_NAME)
        check_connection(engine)

        create_tables(engine)

        df = read_processed_csv()
        logger.info("Read %d processed rows from CSV", len(df))

        rows_inserted = insert_orders(engine, df)
        logger.info("Inserted %d rows into table orders", rows_inserted)
        if rows_inserted != len(df):
            raise RuntimeError(f"So dong trong DB ({rows_inserted}) khac so dong trong CSV ({len(df)})")

        star_counts = build_star_schema(engine)
        logger.info("Star schema rows: %s", star_counts)
    except SQLAlchemyError as error:
        raise RuntimeError(f"Database error: {explain_db_error(error)} | Chi tiet: {error}") from error
    finally:
        engine.dispose()  # đóng mọi kết nối

    return {"rows_inserted": rows_inserted, "star_schema": star_counts}


def main() -> int:
    """Hàm chạy khi gõ: python src/load.py"""
    config.setup_logging()
    try:
        result = run_load()
        print(f"Inserted {result['rows_inserted']} records into PostgreSQL.")
        return 0
    except Exception as error:  # noqa: BLE001
        logger.error("Load failed: %s", error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
