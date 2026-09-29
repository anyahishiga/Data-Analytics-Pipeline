"""
test_s3_mock.py  (TUỲ CHỌN)
===========================
Test phần S3 (upload / đọc) MÀ KHÔNG CẦN tài khoản AWS, bằng thư viện "moto"
- moto giả lập S3 ngay trong bộ nhớ máy bạn, không có gì được gửi lên AWS thật.

Cài thêm để chạy (không nằm trong requirements.txt):
    pip install moto
Nếu chưa cài moto thì file này tự bị SKIP.
"""

import boto3
import pandas as pd
import pytest

pytest.importorskip("moto")  # không có moto -> bỏ qua cả file
from moto import mock_aws  # noqa: E402

import config  # noqa: E402
import ingest  # noqa: E402

BUCKET = "cloud-data-pipeline-unit-test"
REGION = "ap-southeast-1"


@pytest.fixture
def fake_s3(monkeypatch):
    """Dựng 1 S3 giả với 1 bucket trống. Dùng key giả để không bao giờ đụng tới AWS thật."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setattr(config, "AWS_REGION", REGION)

    with mock_aws():
        client = boto3.client("s3", region_name=REGION)
        client.create_bucket(
            Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION}
        )
        yield client


def test_upload_and_read_back(fake_s3, tmp_path):
    local_file = tmp_path / "orders.csv"
    local_file.write_text("order_id,quantity\nORD000001,2\nORD000002,5\n", encoding="utf-8")

    s3_uri = ingest.upload_to_s3(local_file, BUCKET, "raw/orders.csv")
    assert s3_uri == f"s3://{BUCKET}/raw/orders.csv"

    df = ingest.read_csv_from_s3(BUCKET, "raw/orders.csv")
    assert list(df["order_id"]) == ["ORD000001", "ORD000002"]
    assert list(df["quantity"]) == ["2", "5"]


def test_upload_to_missing_bucket_gives_friendly_error(fake_s3, tmp_path):
    local_file = tmp_path / "orders.csv"
    local_file.write_text("a\n1\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Bucket khong ton tai"):
        ingest.upload_to_s3(local_file, "bucket-that-does-not-exist", "raw/orders.csv")


def test_upload_missing_local_file(fake_s3, tmp_path):
    with pytest.raises(FileNotFoundError):
        ingest.upload_to_s3(tmp_path / "khong_co_file.csv", BUCKET, "raw/orders.csv")
