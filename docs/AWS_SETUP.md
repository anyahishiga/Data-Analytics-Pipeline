# Cấu hình AWS cho project (S3 + IAM)

> Tài liệu này **không giả định bạn đã biết AWS** và **không giả định tài khoản có tài nguyên miễn phí**.
> Giao diện AWS Console thay đổi theo thời gian; tên nút có thể khác đôi chút nhưng các bước giữ nguyên.
> Chưa muốn dùng AWS ngay? Chạy `python src/pipeline.py --skip-s3` và quay lại đây sau.

## Chi phí của phần S3

Project chỉ lưu 2 file CSV cỡ vài MB. Giá lưu trữ S3 tính theo GB-tháng (vài cent/GB), nên chi phí thực tế gần như bằng 0 (vài cent hoặc ít hơn). Tuy vậy hãy làm **Bước 2** (đặt cảnh báo chi phí) trước khi làm gì khác, và kiểm tra bảng giá hiện tại tại <https://aws.amazon.com/s3/pricing/>.

## Bước 1. Tài khoản AWS và bảo mật cơ bản

1. Đăng ký tại <https://aws.amazon.com/> (cần email và thẻ thanh toán quốc tế).
2. Đăng nhập bằng **root user** (email đăng ký) chỉ để làm vài việc thiết lập, sau đó **không dùng root cho công việc hằng ngày**.
3. Bật MFA (xác thực 2 lớp) cho root: góc trên phải bấm tên tài khoản → **Security credentials** → **Assign MFA device**.
4. Chọn region ở góc trên bên phải: **Asia Pacific (Singapore) `ap-southeast-1`** (gần Việt Nam, khớp với `.env.example`). *Dùng cùng một region cho mọi thứ (S3, Redshift).*

## Bước 2. Đặt cảnh báo chi phí (làm ngay!)

1. Tìm dịch vụ **Billing and Cost Management** → **Budgets** → **Create budget**.
2. Chọn mẫu **Zero spend budget** (báo email ngay khi phát sinh chi phí), hoặc **Monthly cost budget** với hạn mức nhỏ (ví dụ 5 USD).
3. Nhập email nhận cảnh báo → tạo.

## Bước 3. Tạo S3 bucket

*Bucket* là "ổ đĩa" trên S3. Tên bucket **duy nhất trên toàn thế giới**.

1. Vào dịch vụ **S3** → **Create bucket**.
2. **Bucket name**: ví dụ `cloud-data-pipeline-tenban-2026` (chữ thường, số, dấu `-`; thêm tên/năm sinh để không trùng người khác). *Ghi lại chính xác tên này.*
3. **AWS Region**: `Asia Pacific (Singapore) ap-southeast-1`.
4. **Block all public access**: để **BẬT** (mặc định). Dữ liệu của bạn phải là riêng tư.
5. Các mục còn lại để mặc định → **Create bucket**.

**Về thư mục `raw/` và `processed/`:** S3 không có thư mục thật. Khi pipeline upload file có key `raw/orders.csv`, thư mục `raw/` tự xuất hiện. Nếu muốn tự tạo trước: mở bucket → **Create folder** → `raw`, rồi làm lại với `processed`.

```
s3://<bucket>/raw/        ← dữ liệu thô do ingest.py upload
s3://<bucket>/processed/  ← dữ liệu sạch do transform.py upload
```

## Bước 4. Tạo IAM User riêng cho pipeline

**Vì sao không dùng root?** Root có quyền vô hạn; lỡ lộ key là mất cả tài khoản. Ta tạo một IAM User chỉ có quyền đọc/ghi *đúng bucket này*. Đó là nguyên tắc **least privilege** (quyền tối thiểu).

### 4.1 Tạo policy giới hạn quyền

1. Dịch vụ **IAM** → **Policies** → **Create policy** → chọn tab **JSON**.
2. Dán nội dung sau, **thay `YOUR_BUCKET_NAME` (2 chỗ) bằng tên bucket của bạn**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListTheBucket",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME"
    },
    {
      "Sid": "ReadWriteFilesInTheBucket",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/*"
    }
  ]
}
```

3. **Next** → đặt tên `cloud-data-pipeline-s3-access` → **Create policy**.

### 4.2 Tạo user và gắn policy

1. **IAM** → **Users** → **Create user** → tên `pipeline-user`.
2. **Không** cần bật quyền đăng nhập Console. **Next**.
3. **Attach policies directly** → tìm `cloud-data-pipeline-s3-access` → tick chọn → **Next** → **Create user**.

### 4.3 Tạo Access Key

1. Bấm vào user `pipeline-user` → tab **Security credentials** → **Create access key**.
2. Chọn use case **Application running outside AWS** (hoặc **Local code**) → **Next** → **Create access key**.
3. Bạn sẽ thấy **Access key ID** và **Secret access key**. **Secret chỉ hiện một lần**: bấm **Download .csv** và cất kỹ.

> **Với Role thì sao?** *IAM Role* là danh tính "mượn tạm", dùng khi *dịch vụ AWS* cần quyền (ví dụ Redshift đọc S3, hoặc code chạy trên EC2). Project này chạy trên máy bạn nên dùng IAM User + access key. Ở Phase Redshift bạn sẽ tạo một IAM **Role** cho Redshift.

## Bước 5. Điền file `.env`

```powershell
Copy-Item .env.example .env
code .env        # mở bằng VS Code
```

Sửa các dòng sau (không dấu nháy, không khoảng trắng quanh dấu `=`):

```
AWS_ACCESS_KEY_ID=AKIA...............
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_REGION=ap-southeast-1
S3_BUCKET_NAME=cloud-data-pipeline-tenban-2026
```

- **Lưu file bằng VS Code (UTF-8).** Đừng tạo `.env` bằng `echo ... > .env` trong PowerShell 5 (nó ghi UTF-16, python-dotenv đọc sẽ lỗi).
- **Không commit `.env` lên GitHub** (đã có trong `.gitignore`). Xem `GITHUB_GUIDE.md`.

## Bước 6. Kiểm tra

```powershell
python src/generate_data.py    # nếu chưa có data/raw/orders.csv
python src/ingest.py
```

Kết quả mong đợi:

```
INFO Starting ingestion...
INFO Reading CSV...
INFO CSV has 10000 rows and 12 columns
INFO Uploading to S3...
INFO Upload successful. File is at s3://cloud-data-pipeline-tenban-2026/raw/orders.csv
```

Sau đó vào S3 Console → bucket của bạn → thấy thư mục `raw/` chứa `orders.csv`.

## Lỗi thường gặp

| Thông báo | Nguyên nhân | Cách sửa |
|---|---|---|
| `S3_BUCKET_NAME chua duoc cau hinh` | Chưa điền `.env` | Điền tên bucket thật |
| `Khong tim thay AWS key` / `Unable to locate credentials` | Thiếu key trong `.env`, hoặc `.env` không nằm ở thư mục gốc project | Kiểm tra tên biến đúng `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| `InvalidAccessKeyId` | Key sai/đã bị xoá | Tạo access key mới ở Bước 4.3 |
| `SignatureDoesNotMatch` | Secret key sai (copy thiếu/thừa ký tự, có khoảng trắng) | Copy lại, không có khoảng trắng hoặc dấu nháy |
| `NoSuchBucket` | Sai tên bucket hoặc sai region | So sánh `S3_BUCKET_NAME` và `AWS_REGION` với S3 Console |
| `AccessDenied` (403) | Policy sai/chưa gắn cho user, hoặc `YOUR_BUCKET_NAME` chưa được thay | Sửa policy ở Bước 4.1 |
| Lỗi kết nối / timeout | Mất Internet hoặc firewall | Thử lại; kiểm tra mạng |

## Dọn dẹp khi không dùng nữa

S3 → chọn bucket → **Empty** (xoá hết file) → **Delete** bucket. IAM → Users → xoá `pipeline-user` (hoặc vô hiệu hoá access key).
