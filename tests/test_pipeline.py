"""
test_pipeline.py
================
Test tự động bằng pytest. Chạy:

    pytest -v -rs

Giải thích nhanh:
    - Hàm bắt đầu bằng "test_" là 1 bài test. Trong đó dùng "assert" để khẳng định điều gì đó đúng.
      assert sai -> test FAILED (đỏ), assert đúng -> PASSED (xanh).
    - Mỗi test dựng 1 DataFrame nhỏ (1-4 dòng) rồi chạy hàm cần kiểm tra -> dễ đọc, chạy nhanh.
    - test_database_connection cần PostgreSQL đang chạy; nếu chưa có, nó tự SKIP (bỏ qua)
      và -rs sẽ cho bạn thấy lý do.
"""

import pandas as pd
import pytest

import config
import generate_data
import load
import transform


# ------------------------------------------------------------------
# HÀM HỖ TRỢ
# ------------------------------------------------------------------
def make_row(**overrides) -> dict:
    """
    Tạo 1 dòng raw HỢP LỆ (mọi giá trị là chuỗi, giống dữ liệu vừa đọc từ CSV).
    Muốn test lỗi nào thì ghi đè đúng cột đó, ví dụ: make_row(quantity="0")
    """
    row = {
        "order_id": "ORD000001",
        "customer_id": "CUS00001",
        "order_date": "2026-01-15",
        "product_id": "P001",
        "product_name": "Laptop ASUS",
        "category": "Electronics",
        "quantity": "2",
        "unit_price": "10000000",
        "discount": "0.10",
        "payment_method": "Banking",
        "city": "Thu Dau Mot",
        "status": "Completed",
    }
    row.update(overrides)
    return row


def make_df(*rows) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


# ------------------------------------------------------------------
# 1. TẠO CSV
# ------------------------------------------------------------------
def test_default_dataset_has_at_least_10000_rows():
    assert generate_data.NUM_ROWS >= 10_000


def test_csv_generation(tmp_path):
    rows = generate_data.generate_orders(num_rows=1000)
    csv_path = tmp_path / "orders.csv"
    generate_data.save_orders_to_csv(rows, csv_path)

    assert csv_path.exists()
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    assert len(df) == 1000
    assert list(df.columns) == generate_data.COLUMNS


def test_generated_data_is_intentionally_dirty():
    df = pd.DataFrame(generate_data.generate_orders(num_rows=1000)).astype(str)

    assert df.duplicated().sum() > 0                      # có dòng trùng hoàn toàn
    assert df["order_id"].duplicated().sum() > 0          # có order_id bị lặp
    assert (df == "").any().any()                         # có ô bị thiếu


# ------------------------------------------------------------------
# 2. TRÙNG LẶP
# ------------------------------------------------------------------
def test_duplicate_removal():
    df = make_df(
        make_row(order_id="ORD000001"),
        make_row(order_id="ORD000001"),                    # trùng hoàn toàn
        make_row(order_id="ORD000001", quantity="5"),      # cùng order_id, khác nội dung
        make_row(order_id="ORD000002"),
    )
    result, removed = transform.remove_duplicates(transform.clean_text(df))

    assert removed == 2
    assert list(result["order_id"]) == ["ORD000001", "ORD000002"]
    assert result.iloc[0]["quantity"] == "2"               # giữ dòng xuất hiện đầu tiên


# ------------------------------------------------------------------
# 3. GIÁ TRỊ THIẾU
# ------------------------------------------------------------------
def test_missing_required_value_is_rejected():
    df = make_df(make_row(), make_row(order_id="ORD000002", customer_id=None))
    clean, rejected, _ = transform.transform_data(df)

    assert list(clean["order_id"]) == ["ORD000001"]
    assert list(rejected["order_id"]) == ["ORD000002"]
    assert rejected.iloc[0]["reject_reason"] == "missing_required_value"


def test_missing_optional_values_are_filled():
    df = make_df(
        make_row(order_id="ORD000001"),                                    # dòng đầy đủ
        make_row(order_id="ORD000002", category=None, discount=None, city=None),
    )
    clean, rejected, _ = transform.transform_data(df)

    assert len(rejected) == 0
    row = clean[clean["order_id"] == "ORD000002"].iloc[0]
    assert row["discount"] == 0                       # discount thiếu -> 0
    assert row["category"] == "Electronics"           # lấy từ dòng khác cùng product_id P001
    assert row["city"] == "Unknown"                   # city thiếu -> Unknown


# ------------------------------------------------------------------
# 4. TOTAL_AMOUNT
# ------------------------------------------------------------------
def test_total_amount_calculation():
    # 2 * 10.000.000 * (1 - 0.1) = 18.000.000
    clean, _, _ = transform.transform_data(make_df(make_row()))
    assert clean.iloc[0]["total_amount"] == 18_000_000


def test_total_amount_without_discount():
    clean, _, _ = transform.transform_data(make_df(make_row(quantity="3", unit_price="250000", discount="0")))
    assert clean.iloc[0]["total_amount"] == 750_000


# ------------------------------------------------------------------
# 5. GIÁ TRỊ KHÔNG HỢP LỆ
# ------------------------------------------------------------------
@pytest.mark.parametrize("bad_quantity", ["0", "-1", "abc", "2.5"])
def test_invalid_quantity_is_rejected(bad_quantity):
    clean, rejected, _ = transform.transform_data(make_df(make_row(quantity=bad_quantity)))
    assert len(clean) == 0
    assert len(rejected) == 1


@pytest.mark.parametrize("bad_price", ["0", "-100000", "abc"])
def test_invalid_price_is_rejected(bad_price):
    clean, rejected, _ = transform.transform_data(make_df(make_row(unit_price=bad_price)))
    assert len(clean) == 0
    assert len(rejected) == 1


@pytest.mark.parametrize("bad_discount", ["1.5", "-0.1", "abc"])
def test_invalid_discount_is_rejected(bad_discount):
    clean, rejected, _ = transform.transform_data(make_df(make_row(discount=bad_discount)))
    assert len(clean) == 0
    assert len(rejected) == 1


@pytest.mark.parametrize("edge_discount", ["0", "1"])
def test_discount_boundaries_are_valid(edge_discount):
    clean, rejected, _ = transform.transform_data(make_df(make_row(discount=edge_discount)))
    assert len(clean) == 1
    assert len(rejected) == 0


def test_invalid_date_status_and_payment_are_rejected():
    df = make_df(
        make_row(order_id="ORD000001", order_date="2026-13-45"),
        make_row(order_id="ORD000002", status="Invalid_Status"),
        make_row(order_id="ORD000003", payment_method="Bitcoin"),
        make_row(order_id="ORD000004"),
    )
    clean, rejected, _ = transform.transform_data(df)

    assert list(clean["order_id"]) == ["ORD000004"]
    assert len(rejected) == 3


# ------------------------------------------------------------------
# 6. CHUẨN HOÁ CHỮ
# ------------------------------------------------------------------
def test_text_normalization():
    df = make_df(
        make_row(order_id="ORD000001", city="  ha noi ", category="electronics", status="completed"),
        make_row(order_id="ORD000002", city="HCM", category="ELECTRONICS", payment_method="credit card"),
    )
    clean, rejected, _ = transform.transform_data(df)

    assert len(rejected) == 0
    assert list(clean["city"]) == ["Ha Noi", "Ho Chi Minh"]
    assert set(clean["category"]) == {"Electronics"}
    assert list(clean["status"]) == ["Completed", "Completed"]
    assert list(clean["payment_method"]) == ["Banking", "Credit Card"]


# ------------------------------------------------------------------
# 7. CHẠY TRÊN TOÀN BỘ DỮ LIỆU GIẢ LẬP
# ------------------------------------------------------------------
def test_full_transform_on_generated_data():
    raw = pd.DataFrame(generate_data.generate_orders(num_rows=2000)).astype(str)
    raw = raw.replace("", pd.NA)  # giống hệt khi đọc CSV: ô trống -> thiếu
    clean, rejected, stats = transform.transform_data(raw)

    # Mọi dòng đầu vào đều phải được "kiểm toán": hoặc sạch, hoặc trùng, hoặc bị loại
    assert stats["rows_clean"] + stats["duplicates_removed"] + stats["rows_rejected"] == 2000
    assert stats["rows_clean"] > 1500

    # Dữ liệu sạch phải thoả mọi quy tắc
    assert clean["order_id"].is_unique
    assert (clean["quantity"] > 0).all()
    assert (clean["unit_price"] > 0).all()
    assert clean["discount"].between(0, 1).all()
    assert clean["status"].isin(config.VALID_STATUSES).all()
    assert clean["payment_method"].isin(config.VALID_PAYMENT_METHODS).all()
    assert clean.isna().sum().sum() == 0
    expected_total = (clean["quantity"] * clean["unit_price"] * (1 - clean["discount"])).round(2)
    assert (clean["total_amount"] == expected_total).all()


# ------------------------------------------------------------------
# 8. DATABASE (cần PostgreSQL đang chạy)
# ------------------------------------------------------------------
def test_database_connection():
    engine = load.get_engine()
    try:
        load.check_connection(engine)
    except RuntimeError as error:
        pytest.skip(f"PostgreSQL chua san sang, bo qua test nay: {error}")
    finally:
        engine.dispose()
