"""
pipeline.py
===========
Chạy TOÀN BỘ pipeline từ đầu đến cuối bằng MỘT lệnh:

    python src/pipeline.py                 # đầy đủ: có AWS S3 + PostgreSQL
    python src/pipeline.py --skip-s3       # chưa có AWS: bỏ qua các bước S3
    python src/pipeline.py --regenerate    # tạo lại file CSV giả lập từ đầu

Thứ tự các bước:
    [1] Data ingestion       tạo (hoặc đọc) data/raw/orders.csv
    [2] Upload raw data      đẩy orders.csv lên s3://bucket/raw/
    [3] Data transformation  đọc raw (từ S3), làm sạch bằng Pandas, lưu orders_clean.csv
    [4] Upload processed     đẩy orders_clean.csv lên s3://bucket/processed/
    [5] Load database        nạp vào PostgreSQL + dựng Star Schema
    [6] Data quality         chạy sql/data_quality.sql, lưu data_quality_report.csv
    Cuối cùng: in bảng tóm tắt (summary).

Nguyên tắc xử lý lỗi: bước nào lỗi thì DỪNG pipeline (các bước sau phụ thuộc bước trước),
ghi lỗi vào log, các bước chưa chạy hiển thị "NOT RUN" và lệnh trả về mã lỗi 1.
"""

import argparse
import logging
import sys
import time

import pandas as pd

import config
import data_quality
import generate_data
import ingest
import load
import transform

logger = logging.getLogger(__name__)

LINE = "=" * 44


def ensure_raw_data(regenerate: bool = False) -> dict:
    """Bước 1: tạo file CSV nếu chưa có (hoặc nếu --regenerate), rồi đếm số dòng."""
    if regenerate or not config.RAW_DATA_PATH.exists():
        generate_data.run_generate()
    else:
        logger.info("Found existing raw file %s (use --regenerate to create a new one)",
                    config.RAW_DATA_PATH)

    rows = len(pd.read_csv(config.RAW_DATA_PATH, dtype=str))
    logger.info("Raw CSV has %d rows", rows)
    return {"rows": rows}


def print_summary(step_results: list, outputs: dict, use_s3: bool, seconds: float, success: bool) -> None:
    """In bảng tóm tắt ra màn hình và ghi vào log."""
    lines = [LINE, "CLOUD DATA ANALYTICS PIPELINE", LINE, ""]
    for number, (name, status) in enumerate(step_results, start=1):
        lines.append(f"[{number}] {name:<22} {status}")
    lines.append("")

    stats = outputs.get("Data transformation")
    if stats:
        invalid = stats["rows_read"] - stats["rows_clean"]
        lines.append(f"Total records:   {stats['rows_read']}")
        lines.append(f"Valid records:   {stats['rows_clean']}")
        lines.append(f"Invalid records: {invalid}  "
                     f"(duplicates removed: {stats['duplicates_removed']}, rejected: {stats['rows_rejected']})")

    report = outputs.get("Data quality")
    if report is not None:
        passed = int((report["status"] == "PASS").sum())
        lines.append(f"Data quality:    {passed}/{len(report)} checks passed")

    if use_s3 and success:
        bucket = config.S3_BUCKET_NAME
        lines.append(f"S3 raw:          s3://{bucket}/{config.S3_RAW_KEY}")
        lines.append(f"S3 processed:    s3://{bucket}/{config.S3_PROCESSED_KEY}")

    lines.append(f"Duration:        {seconds:.1f} seconds")
    lines.append("")
    lines.append("Pipeline completed successfully." if success else "Pipeline FAILED. See logs/pipeline.log")
    lines.append(LINE)

    print()
    for line in lines:
        print(line)
    logger.info("Pipeline finished: %s", "SUCCESS" if success else "FAILED")


def run_pipeline(use_s3: bool = True, regenerate: bool = False) -> bool:
    """Chạy pipeline. Trả về True nếu mọi bước đều chạy được."""
    started = time.time()
    logger.info("Starting pipeline (use_s3=%s)", use_s3)

    # (tên bước, hàm thực hiện, bước này có cần S3 không?)
    steps = [
        ("Data ingestion", lambda: ensure_raw_data(regenerate), False),
        ("Upload raw data", ingest.run_ingestion, True),
        ("Data transformation", lambda: transform.run_transform(use_s3), False),
        ("Upload processed", transform.upload_processed_data, True),
        ("Load database", load.run_load, False),
        ("Data quality", data_quality.run_data_quality, False),
    ]

    step_results = []   # [(tên bước, trạng thái)]
    outputs = {}        # kết quả trả về của từng bước (để in summary)
    failed = False

    for name, function, needs_s3 in steps:
        if failed:
            step_results.append((name, "NOT RUN"))
            continue
        if needs_s3 and not use_s3:
            logger.info("Skipping step '%s' (--skip-s3)", name)
            step_results.append((name, "SKIPPED"))
            continue

        logger.info("--- Step: %s ---", name)
        try:
            outputs[name] = function()
            status = "SUCCESS"
            # Check chất lượng FAIL không làm pipeline dừng, nhưng phải cảnh báo rõ.
            if name == "Data quality" and (outputs[name]["status"] == "FAIL").any():
                status = "WARNING"
                logger.warning("Some data quality checks FAILED - see data_quality_report.csv")
            step_results.append((name, status))
        except Exception as error:  # noqa: BLE001 - mọi lỗi đều phải được ghi lại
            logger.error("Step '%s' failed: %s", name, error)
            logger.debug("Details:", exc_info=True)
            step_results.append((name, "FAILED"))
            failed = True

    print_summary(step_results, outputs, use_s3, time.time() - started, success=not failed)
    return not failed


def main() -> int:
    """Hàm chạy khi gõ: python src/pipeline.py"""
    config.setup_logging()

    parser = argparse.ArgumentParser(description="Run the whole e-commerce analytics pipeline.")
    parser.add_argument("--skip-s3", action="store_true",
                        help="bo qua cac buoc AWS S3 (dung khi chua co tai khoan AWS)")
    parser.add_argument("--regenerate", action="store_true",
                        help="tao lai file data/raw/orders.csv tu dau")
    args = parser.parse_args()

    success = run_pipeline(use_s3=not args.skip_s3, regenerate=args.regenerate)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
