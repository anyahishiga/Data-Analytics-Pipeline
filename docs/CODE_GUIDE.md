# Hướng dẫn đọc code: từng file, từng function

Đọc theo đúng thứ tự dữ liệu chảy qua pipeline sẽ dễ hiểu nhất.

```
config.py ──(mọi file đều dùng)
generate_data.py ─► data/raw/orders.csv
ingest.py        ─► S3 raw/            (và cung cấp hàm S3 cho transform.py)
transform.py     ─► data/processed/*.csv ─► S3 processed/
load.py          ─► PostgreSQL (orders + star schema)
data_quality.py  ─► data/processed/data_quality_report.csv
pipeline.py      ─► gọi tất cả các file trên theo thứ tự
```

Quy ước chung ở mọi file trong `src/`:

- `run_xxx()` là hàm **làm việc thật**; nếu lỗi thì *ném exception*.
- `main()` là hàm **cho dòng lệnh** (`python src/xxx.py`): gọi `run_xxx()`, bắt lỗi, in thông báo, trả về mã thoát `0` (OK) hoặc `1` (lỗi).
- `pipeline.py` gọi các hàm `run_xxx()` (không gọi `main()`), nhờ vậy tự kiểm soát việc dừng/tiếp tục khi có lỗi.

---

## `src/config.py` — cấu hình trung tâm

Không chứa logic xử lý dữ liệu. Chỉ có hằng số và 3 hàm nhỏ.

| Thành phần | Chức năng |
|---|---|
| `BASE_DIR`, `RAW_DATA_PATH`, `PROCESSED_DATA_PATH`... | Đường dẫn tới thư mục/file (dùng `pathlib` nên chạy tốt cả Windows lẫn Linux). |
| `load_dotenv(...)` | Đọc file `.env` và nạp `KEY=VALUE` vào biến môi trường. |
| `AWS_REGION`, `S3_BUCKET_NAME`, `DB_*` | Lấy từ `.env` bằng `os.getenv("TÊN", "giá trị mặc định")`. Key AWS **không** đọc ở đây: `boto3` tự lấy từ biến môi trường. |
| `S3_RAW_KEY`, `S3_PROCESSED_KEY` | Tên file bên trong bucket: `raw/orders.csv`, `processed/orders_clean.csv`. |
| `VALID_STATUSES`, `VALID_PAYMENT_METHODS`, `CITY_ALIASES` | Quy tắc nghiệp vụ dùng chung cho `transform.py`, `generate_data.py` và test. |
| `get_s3_bucket()` | Trả về tên bucket; nếu chưa điền `.env` thì báo lỗi dễ hiểu (thay vì lỗi AWS khó đọc). |
| `get_database_url()` | Dựng địa chỉ kết nối PostgreSQL bằng `URL.create` (an toàn với mật khẩu có ký tự đặc biệt). |
| `setup_logging()` | Cấu hình `logging` ghi vào **màn hình + file** `logs/pipeline.log`. Có bảo vệ để gọi nhiều lần không bị ghi trùng. |

## `src/generate_data.py` — tạo dữ liệu giả lập

Dữ liệu được tạo bằng `random.seed(42)` nên **lần nào chạy cũng ra cùng một file**.

| Hàm | Làm gì |
|---|---|
| `random_order_date()` | Chọn tháng theo trọng số `MONTH_WEIGHTS` (tháng sau đông đơn hơn) rồi chọn ngày trong tháng. |
| `create_valid_order(n)` | Tạo 1 đơn hợp lệ dạng `dict` (`order_id = ORD000001`, khách, ngày, sản phẩm, số lượng...). |
| `make_missing(row)` | Xoá trống 1 ô ngẫu nhiên (khách, sản phẩm, tên, nhóm hàng, giảm giá, thanh toán, thành phố, trạng thái). |
| `make_invalid(row)` | Gán 1 giá trị **sai** (số lượng ≤ 0 hoặc "abc", giá ≤ 0, discount > 1 hoặc < 0, ngày sai, status/payment lạ). |
| `make_messy(row)` | Viết hoa/thường/khoảng trắng lộn xộn (`hcm`, `  ha noi  `, `electronics`, `completed`) — vẫn **sửa được**. |
| `generate_orders(num_rows, seed)` | Ghép tất cả: tạo dòng hợp lệ → làm bẩn ngẫu nhiên → thêm dòng trùng lặp vào cuối. Trả về `list[dict]`. |
| `save_orders_to_csv(rows, path)` | Ghi ra CSV UTF-8 bằng `csv.DictWriter`. |
| `run_generate(num_rows)` | Tạo + lưu vào `data/raw/orders.csv`. |
| `main()` | Đọc tham số `--rows`, gọi `run_generate`. |

Với 10.000 dòng: 150 dòng trùng hệt, 30 dòng trùng `order_id` khác nội dung, 300 dòng thiếu ô, 250 dòng giá trị sai, 400 dòng chữ lộn xộn.

## `src/ingest.py` — đưa dữ liệu lên S3

| Hàm | Làm gì |
|---|---|
| `get_s3_client()` | Tạo client `boto3` cho S3 ở region trong `.env`. |
| `explain_aws_error(error)` | Đổi lỗi AWS khó hiểu (`NoSuchBucket`, `AccessDenied`, `InvalidAccessKeyId`...) thành lời khuyên tiếng Việt. |
| `upload_to_s3(local_path, bucket_name, s3_key)` | Upload 1 file: kiểm tra file tồn tại, gọi `s3_client.upload_file`, trả về `s3://bucket/key`. Bắt lỗi và ném `RuntimeError` có giải thích. |
| `read_csv_from_s3(bucket_name, s3_key)` | `get_object` để lấy nội dung file trên S3 rồi `pd.read_csv` thành DataFrame (mọi cột đọc dạng chữ). Dùng trong `transform.py`. |
| `run_ingestion()` | Log `Starting ingestion...` → kiểm tra file → `Reading CSV...` → `Uploading to S3...` → `Upload successful.` |
| `main()` | Gọi `run_ingestion()` cho dòng lệnh. |

## `src/transform.py` — ETL bằng Pandas

Nguyên tắc: **mỗi hàm làm đúng 1 việc**, và những dòng bị loại **không bị mất** mà đi vào `orders_rejected.csv` kèm `reject_reason`.

| Hàm | Làm gì |
|---|---|
| `split_invalid(df, is_invalid, reason)` | Hàm hỗ trợ trung tâm: tách `df` thành (dòng hợp lệ, dòng bị loại + lý do). |
| `combine_rejected(parts)` | Gộp nhiều bảng "bị loại" thành một. |
| `check_columns(df)` | Chắc chắn file raw có đủ 12 cột. |
| `clean_text(df)` | Cắt khoảng trắng mọi ô; ô rỗng → thiếu (`NaN`). |
| `remove_duplicates(df)` | Bỏ dòng trùng hệt, rồi bỏ dòng trùng `order_id` (giữ dòng đầu). Trả về số dòng đã bỏ. |
| `handle_missing_values(df)` | Thiếu cột **bắt buộc** → loại dòng. `discount` thiếu → 0. `product_name`/`category` thiếu → lấy từ dòng khác cùng `product_id`. Còn thiếu → `Unknown`. |
| `validate_data_types(df)` | `order_date` phải là `YYYY-MM-DD`; `quantity`, `unit_price`, `discount` phải là số (dùng `errors="coerce"`); rồi **đổi kiểu thật**. |
| `validate_quantity(df)` | Số nguyên > 0. |
| `validate_price(df)` | `unit_price` > 0. |
| `validate_discount(df)` | 0 ≤ discount ≤ 1. |
| `validate_status_and_payment(df)` | Chuẩn hoá chữ (`completed` → `Completed`) rồi chỉ giữ giá trị trong danh sách hợp lệ. |
| `add_total_amount(df)` | `total_amount = quantity * unit_price * (1 - discount)`, làm tròn 2 số lẻ. |
| `normalize_city(df)` | Dọn khoảng trắng, `Title Case`, tra `CITY_ALIASES` (`hcm` → `Ho Chi Minh`, `hanoi` → `Ha Noi`). |
| `normalize_category(df)` | `electronics` → `Electronics`. |
| `transform_data(raw_df)` | **Ghép tất cả các bước trên theo đúng thứ tự.** Trả về `(clean_df, rejected_df, stats)`. Hàm này không đụng tới file/S3 nên rất dễ test. |
| `read_raw_data(use_s3)` | Đọc raw từ S3 (mặc định) hoặc từ file local nếu `--skip-s3`. |
| `save_processed_data(clean, rejected)` | Ghi `orders_clean.csv` và `orders_rejected.csv`. |
| `run_transform(use_s3)` | Đọc → transform → lưu, ghi log thống kê. |
| `upload_processed_data()` | Upload `orders_clean.csv` lên `s3://bucket/processed/`. |
| `main()` | Dòng lệnh: `python src/transform.py [--skip-s3]`. |

## `src/load.py` — nạp vào PostgreSQL

| Hàm | Làm gì |
|---|---|
| `get_engine()` | Tạo SQLAlchemy `Engine` từ thông tin `.env`. |
| `explain_db_error(error)` | Lời khuyên cho lỗi hay gặp: sai mật khẩu, chưa tạo database, PostgreSQL chưa chạy... |
| `check_connection(engine)` | Chạy `SELECT 1` thử kết nối. |
| `run_sql_file(engine, path)` | Đọc 1 file `.sql` và chạy trong **một giao dịch** (lỗi giữa chừng → hoàn tác hết). |
| `create_tables(engine)` | Chạy `sql/create_tables.sql` (`CREATE TABLE IF NOT EXISTS`, nên chạy lại vẫn an toàn). |
| `read_processed_csv()` | Đọc `orders_clean.csv`, đổi `order_date` thành kiểu ngày. |
| `insert_orders(engine, df)` | Trong 1 giao dịch: `TRUNCATE` bảng `orders` rồi `df.to_sql(...)`. Chạy pipeline nhiều lần **không bị trùng dữ liệu** (full refresh). |
| `build_star_schema(engine)` | Chạy `sql/build_star_schema.sql`, trả về số dòng từng bảng. |
| `run_load()` | Kết nối → tạo bảng → đọc CSV → chèn → kiểm tra số dòng khớp → dựng star schema. |
| `main()` | In `Inserted N records into PostgreSQL.` |

## `src/data_quality.py` — kiểm tra chất lượng

| Hàm | Làm gì |
|---|---|
| `run_data_quality()` | Chạy `sql/data_quality.sql` (9 phép kiểm tra), thêm cột `status` (`PASS` nếu `invalid_rows = 0`, ngược lại `FAIL`), lưu `data_quality_report.csv`, ghi log từng check. |
| `main()` | Dòng lệnh + in bảng kết quả. |

## `src/pipeline.py` — điều phối

| Thành phần | Làm gì |
|---|---|
| `ensure_raw_data(regenerate)` | Bước 1: tạo CSV nếu chưa có (hoặc khi `--regenerate`), đếm số dòng. |
| `run_pipeline(use_s3, regenerate)` | Danh sách 6 bước `(tên, hàm, cần S3?)`, chạy lần lượt. Bước lỗi → ghi log, **dừng**, các bước sau đánh dấu `NOT RUN`. Không có S3 (`--skip-s3`) → bước S3 là `SKIPPED`. Check chất lượng có `FAIL` → bước đó là `WARNING` (không dừng pipeline). |
| `print_summary(...)` | In bảng tóm tắt (tổng dòng / dòng hợp lệ / dòng không hợp lệ...). |
| `main()` | Đọc `--skip-s3`, `--regenerate`; trả về mã thoát 0/1. |

## `sql/` — các file SQL

| File | Dùng ở đâu | Nội dung |
|---|---|---|
| `create_tables.sql` | `load.py` (tự chạy) | Bảng `orders` + 5 bảng star schema (PostgreSQL). |
| `build_star_schema.sql` | `load.py` (tự chạy) | Xoá rồi nạp lại 4 dimension + fact từ `orders`. |
| `data_quality.sql` | `data_quality.py` | 9 phép kiểm tra, trả về `check_name, total_rows, invalid_rows`. |
| `analytics.sql` | Bạn chạy tay (pgAdmin/psql) | 15 truy vấn phân tích có giải thích + output mẫu. |
| `redshift_load.sql` | Bạn chạy tay trong Redshift Query Editor | Phiên bản Redshift: tạo bảng, `COPY` từ S3, dựng star schema. |

## `tests/`

| File | Kiểm tra |
|---|---|
| `test_pipeline.py` | Tạo CSV, xoá trùng, xử lý thiếu, `total_amount`, quantity/price/discount sai, chuẩn hoá chữ, chạy trên cả bộ dữ liệu giả lập, kết nối database. |
| `test_s3_mock.py` | *(tuỳ chọn, cần `pip install moto`)* Upload/đọc S3 bằng S3 giả lập trong bộ nhớ, không cần AWS. |
