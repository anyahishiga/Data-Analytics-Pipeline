# Chuyển từ PostgreSQL local sang AWS Redshift

## ⚠️ ĐỌC TRƯỚC: Redshift TỐN TIỀN

- **Redshift không miễn phí.** Đừng giả định tài khoản của bạn có credit hay free tier: hãy mở trang **Billing → Credits / Free Tier** để xem *chính xác* bạn có gì, và đọc điều kiện của mọi ưu đãi hiển thị trên Console.
- **Redshift Serverless** (cách khuyến nghị cho sinh viên) tính tiền theo **RPU-giờ**, chia theo *giây* khi warehouse đang xử lý. AWS công bố cấu hình nhỏ nhất **4 RPU, từ khoảng 1,50 USD/giờ** (giá cụ thể phụ thuộc region; Singapore có thể cao hơn mức này) + phí lưu trữ theo GB-tháng. Khi không chạy truy vấn thì không tính tiền compute.
- **Redshift Provisioned (cluster)** tính tiền **mỗi giờ cluster tồn tại, kể cả khi bạn không làm gì**. Không dùng cho việc học.
- Nếu quên xoá, tiền vẫn có thể phát sinh (ít nhất là phí lưu trữ). Hãy dọn dẹp ở cuối tài liệu này.
- Bảng giá chính thức: <https://aws.amazon.com/redshift/pricing/>

**Khuyến nghị:**

1. Chỉ làm Phase này **sau khi** pipeline local (PostgreSQL) đã chạy ổn và bạn đã đặt **Budget** (xem `AWS_SETUP.md`, Bước 2).
2. Làm gọn trong 1–2 giờ: chuẩn bị SQL sẵn, chạy nhanh, rồi **xoá ngay**.
3. Nếu không muốn tốn tiền: bạn vẫn có một project hoàn chỉnh với PostgreSQL + Power BI. Phần Redshift chỉ là "nâng cấp lên cloud" và có thể trình bày bằng lý thuyết + ảnh chụp.

---

## Tổng quan: PostgreSQL local → Redshift

```
S3 processed/orders_clean.csv ──COPY──►  Redshift: orders ──INSERT..SELECT──► Star Schema
                                                                              │
                                          Power BI / SQL analytics ◄──────────┘
```

Khác với local (Python `INSERT` từng đợt), Redshift nạp dữ liệu bằng lệnh **`COPY` đọc trực tiếp từ S3**: nhanh và song song. Vì vậy `orders_clean.csv` trên S3 chính là "nguyên liệu" bạn đã chuẩn bị ở các phase trước.

**Điều kiện cần:** đã chạy `python src/pipeline.py` (có S3) và trong S3 có `processed/orders_clean.csv`.

---

## Bước 1. Tạo IAM Role cho Redshift đọc S3

Redshift là *dịch vụ AWS* nên cần một **Role** (không phải access key) để được phép đọc bucket của bạn.

1. **IAM** → **Roles** → **Create role**.
2. **Trusted entity type**: *AWS service* → Use case: **Redshift** → chọn **Redshift - Customizable** → Next.
3. Ở bước gắn policy: chọn **Create policy** (tab JSON) với nội dung (thay tên bucket):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::YOUR_BUCKET_NAME",
        "arn:aws:s3:::YOUR_BUCKET_NAME/*"
      ]
    }
  ]
}
```

   Đặt tên policy `redshift-read-pipeline-bucket`, quay lại tạo role và gắn policy này.
4. Đặt tên role `redshift-s3-read-role` → **Create role**.
5. Mở role vừa tạo và **copy ARN** (dạng `arn:aws:iam::123456789012:role/redshift-s3-read-role`).

## Bước 2. Tạo Redshift Serverless

1. Vào dịch vụ **Amazon Redshift** → chọn **Redshift Serverless** → **Create workgroup** (hoặc *Get started*). Đảm bảo region là `ap-southeast-1`.
2. **Workgroup**
   - Name: `pipeline-wg`
   - **Base capacity: 4 RPU** (mức nhỏ nhất, rẻ nhất; nếu Console không cho chọn 4 thì chọn mức thấp nhất được phép).
3. **Network and security** (xem Bước 3 bên dưới).
4. **Namespace** (nơi chứa database và người dùng)
   - Name: `pipeline-ns`
   - **Database name**: `ecommerce_analytics`
   - **Admin user credentials**: chọn *Customize admin user credentials*; đặt user `admin` và một **mật khẩu mạnh** (ghi lại).
   - **Associated IAM roles**: **Associate IAM roles** → chọn `redshift-s3-read-role` (nên đặt làm *default* nếu Console cho phép).
5. Kiểm tra lại phần **Estimated cost / Base capacity**, rồi **Save configuration / Create**. Chờ vài phút tới khi trạng thái là *Available*.

## Bước 3. Cấu hình mạng và bảo mật

| Việc | Cách làm | Lý do |
|---|---|---|
| **VPC / Subnet** | Dùng *default VPC* và các subnet mặc định của Console | Đơn giản cho người mới |
| **Security group** | Mở **Inbound rule**: Type *Redshift*, Port **5439**, Source **My IP** (IP của riêng bạn) | Chỉ máy bạn được nối vào; **tuyệt đối không** dùng `0.0.0.0/0` |
| **Publicly accessible** | **Tắt** nếu chỉ dùng *Query Editor v2* trên Console. **Bật** chỉ khi cần nối từ Power BI Desktop trên máy bạn | Không để database công khai nếu không cần |
| **Mật khẩu admin** | Mạnh, không đưa lên GitHub | Bí mật |
| **IAM role** | Chỉ quyền đọc đúng bucket của bạn (Bước 1) | Least privilege |

Cách xem IP của bạn: mở <https://checkip.amazonaws.com> và dán dạng `x.x.x.x/32`. Nếu IP nhà mạng đổi, bạn cần cập nhật lại rule.

## Bước 4. Tạo database, schema, bảng

1. Trong Console Redshift → **Query editor v2** → kết nối vào workgroup `pipeline-wg` bằng user `admin` (chọn *Database user name and password*).
2. Chọn database `ecommerce_analytics` (đã được tạo ở Bước 2; nếu bạn để tên khác, có thể tạo thêm bằng `CREATE DATABASE ecommerce_analytics;`).
3. Mở file `sql/redshift_load.sql` trong VS Code, **thay 3 giá trị**:
   - `<YOUR_BUCKET>` → tên bucket
   - `<IAM_ROLE_ARN>` → ARN ở Bước 1
   - `<AWS_REGION>` → `ap-southeast-1`
4. Chạy **KHỐI 1** (tạo schema `ecommerce`) và **KHỐI 2** (tạo 6 bảng) bằng cách bôi đen từng khối → **Run**.

## Bước 5. Nạp dữ liệu từ S3 (COPY)

Chạy **KHỐI 3**:

```sql
COPY orders
FROM 's3://<YOUR_BUCKET>/processed/orders_clean.csv'
IAM_ROLE '<IAM_ROLE_ARN>'
FORMAT AS CSV
IGNOREHEADER 1
REGION '<AWS_REGION>';
```

Ý nghĩa: đọc file CSV trên S3 → nạp vào bảng `orders`; bỏ dòng tiêu đề; dùng Role để có quyền đọc S3.
Sau đó câu `SELECT COUNT(*)` phải ra đúng số dòng của `orders_clean.csv` (ví dụ 9427).

## Bước 6. Dựng Star Schema và kiểm tra

Chạy **KHỐI 4** (5 câu `INSERT ... SELECT`), rồi câu đếm số dòng các bảng ở cuối khối.

## Bước 7. Chạy SQL analytics

Luôn nhớ đầu phiên làm việc: `SET search_path TO ecommerce;`

Dán từng câu trong `sql/data_quality.sql` và `sql/analytics.sql` vào Query Editor. Hai file này viết bằng SQL dùng chung nên chạy được nguyên xi trên cả PostgreSQL và Redshift. Kết quả phải **giống hệt** ở local (nếu cùng dữ liệu).

## Bước 8. Nối Power BI (tuỳ chọn)

Xem `POWER_BI_GUIDE.md`, mục Redshift. Bạn cần: Server = endpoint của workgroup (xem ở trang chi tiết workgroup), port `5439`, database `ecommerce_analytics`, user `admin`. Muốn nối từ máy bạn: bật *Publicly accessible* và mở port 5439 cho IP của bạn ở Bước 3.

---

## Lỗi thường gặp

| Lỗi | Nguyên nhân / cách sửa |
|---|---|
| `COPY` báo **AccessDenied** / *S3ServiceException* | Role chưa được *associate* vào namespace, hoặc policy sai tên bucket. Kiểm tra Bước 1 và Bước 2.4 |
| `COPY` báo lỗi **region / 301 PermanentRedirect** | Thiếu hoặc sai `REGION '...'` (phải là region của *bucket*) |
| `COPY` báo lỗi định dạng dữ liệu | Xem chi tiết: `SELECT * FROM sys_load_error_detail ORDER BY start_time DESC LIMIT 10;` |
| `relation "orders" does not exist` | Quên `SET search_path TO ecommerce;` hoặc chưa chạy KHỐI 2 |
| Không nối được từ Power BI (timeout) | Chưa bật Publicly accessible, hoặc security group chưa mở 5439 cho IP hiện tại của bạn |
| `must be owner of relation ...` | Đang dùng sai user; dùng user `admin` đã tạo |

## 🧹 Dọn dẹp (BẮT BUỘC khi học xong để không mất tiền)

1. Redshift Console → **Serverless dashboard** → vào **Workgroup** `pipeline-wg` → **Actions → Delete**.
2. Xoá **Namespace** `pipeline-ns` (khi hỏi, tick *Delete the associated snapshots* nếu không cần giữ dữ liệu).
3. (Tuỳ chọn) xoá IAM role `redshift-s3-read-role`, và các file trong bucket S3.
4. Sáng hôm sau mở **Billing → Bills** kiểm tra không còn dịch vụ Redshift nào phát sinh phí.
