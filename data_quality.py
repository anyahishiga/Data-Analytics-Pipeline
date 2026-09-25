"""
data_quality.py
===============
Chạy các phép kiểm tra chất lượng dữ liệu (file sql/data_quality.sql) trên bảng "orders"
trong PostgreSQL, rồi lưu báo cáo ra  data/processed/data_quality_report.csv

Ví dụ báo cáo:
    check_name           total_rows  invalid_rows  status
    duplicate_order_id   9409        0             PASS
    quantity_le_0        9409        0             PASS
    ...

Vì sao vẫn kiểm tra dù transform.py đã làm sạch?
    "Tin tưởng nhưng phải kiểm chứng": database là nơi cuối cùng người dùng đọc dữ liệu.
    Nếu ai đó sửa code transform sai, hoặc nạp thêm dữ liệu bằng cách khác, bước này sẽ báo ngay.
    (Redshift còn KHÔNG ép buộc PRIMARY KEY, nên các check kiểu này càng quan trọng.)

Chạy riêng bước này:
    python src/data_quality.py
"""

import logging
import sys

import pandas as pd

import config
from load import get_engine

logger = logging.getLogger(__name__)


def run_data_quality() -> pd.DataFrame:
    """
    Chạy sql/data_quality.sql, thêm cột status (PASS/FAIL), lưu CSV và trả về DataFrame.
    Chỉ ném exception khi KHÔNG chạy được (lỗi kết nối, lỗi SQL);
    còn check nào FAIL thì chỉ ghi cảnh báo vào log.
    """
    logger.info("Running data quality checks...")
    sql = (config.SQL_DIR / "data_quality.sql").read_text(encoding="utf-8")

    engine = get_engine()
    try:
        with engine.connect() as connection:
            result = connection.exec_driver_sql(sql)
            report = pd.DataFrame(result.fetchall(), columns=list(result.keys()))
    finally:
        engine.dispose()

    report["status"] = report["invalid_rows"].apply(lambda count: "PASS" if count == 0 else "FAIL")

    config.DATA_QUALITY_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(config.DATA_QUALITY_REPORT_PATH, index=False, encoding="utf-8")

    for _, row in report.iterrows():
        if row["status"] == "PASS":
            logger.info("Data quality check %-24s PASS", row["check_name"])
        else:
            logger.warning("Data quality check %-24s FAIL (%s invalid rows)",
                           row["check_name"], row["invalid_rows"])

    passed = int((report["status"] == "PASS").sum())
    logger.info("Data quality: %d/%d checks passed. Report: %s",
                passed, len(report), config.DATA_QUALITY_REPORT_PATH)
    return report


def main() -> int:
    """Hàm chạy khi gõ: python src/data_quality.py  (trả về 1 nếu có lỗi khi chạy)"""
    config.setup_logging()
    try:
        report = run_data_quality()
        print(report.to_string(index=False))
        return 0
    except Exception as error:  # noqa: BLE001
        logger.error("Data quality step failed: %s", error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
