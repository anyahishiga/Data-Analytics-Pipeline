# Đưa project lên GitHub

## 1. Cài Git và khai báo danh tính (làm một lần)

1. Tải Git for Windows: <https://git-scm.com/download/win> (giữ các tuỳ chọn mặc định).
2. Mở PowerShell mới và kiểm tra:

```powershell
git --version
git config --global user.name  "Ten Cua Ban"
git config --global user.email "email-dung-cho-github@example.com"
```

## 2. Tạo repository trống trên GitHub

1. Đăng nhập <https://github.com> → nút **+** → **New repository**.
2. **Repository name**: `cloud-data-pipeline`.
3. Chọn **Private** nếu bạn chưa muốn công khai (có thể đổi thành Public sau khi đã kiểm tra kỹ không có bí mật).
4. **Đừng** tick *Add a README*, *.gitignore*, *license* (project đã có sẵn) → **Create repository**.
5. Copy địa chỉ repo, dạng `https://github.com/<ten-ban>/cloud-data-pipeline.git`.

## 3. Đẩy code lên

Chạy trong thư mục gốc của project (PowerShell):

```powershell
cd cloud-data-pipeline

git init
git add .
git status                      # <-- XEM KỸ TRƯỚC KHI COMMIT (xem mục 4)
git commit -m "Initial project"
git branch -M main
git remote add origin https://github.com/<ten-ban>/cloud-data-pipeline.git
git push -u origin main
```

Lần đầu `git push`, cửa sổ đăng nhập GitHub sẽ hiện ra (Git Credential Manager) — đăng nhập bằng trình duyệt là xong. Nếu bị hỏi mật khẩu trong terminal: GitHub **không** nhận mật khẩu tài khoản nữa, hãy dùng *Personal Access Token* (GitHub → Settings → Developer settings → Personal access tokens) hoặc cài GitHub CLI rồi chạy `gh auth login`.

Giải thích từng lệnh:

| Lệnh | Ý nghĩa |
|---|---|
| `git init` | Biến thư mục hiện tại thành 1 repository Git (tạo thư mục ẩn `.git`) |
| `git add .` | Đưa **mọi file không bị `.gitignore` chặn** vào "khu chuẩn bị commit" |
| `git status` | Liệt kê file sắp được commit — dùng để soát lần cuối |
| `git commit -m "..."` | Chụp lại 1 "phiên bản" kèm lời nhắn |
| `git branch -M main` | Đặt tên nhánh chính là `main` |
| `git remote add origin <url>` | Nói với Git: "kho trên GitHub tên là origin, ở địa chỉ này" |
| `git push -u origin main` | Đẩy nhánh `main` lên GitHub (và nhớ để lần sau chỉ cần `git push`) |

## 4. Kiểm tra trước khi push (rất quan trọng)

`git status` phải **KHÔNG** liệt kê: `.env`, `venv/`, `logs/pipeline.log`, `data/raw/orders.csv`, `data/processed/*.csv`.
Phải **CÓ**: `.env.example`, `.gitignore`, `README.md`, `requirements.txt`, `src/`, `sql/`, `tests/`, `docs/`.

Kiểm tra chắc chắn `.env` không bị theo dõi:

```powershell
git ls-files | Select-String "\.env"
# Chỉ được ra:  .env.example
git check-ignore -v .env
# Phải in ra dòng chứa ".gitignore" (nghĩa là .env đang bị chặn)
```

## 5. Vì sao KHÔNG commit `.env`?

- `.env` chứa **AWS Secret Key** và **mật khẩu database**. Ai có chúng là dùng được tài khoản của bạn.
- Git **nhớ toàn bộ lịch sử**: xoá file ở commit sau thì bí mật vẫn còn trong commit cũ. Nếu repo public thì cả thế giới thấy.
- Có các bot quét GitHub 24/7 để tìm key AWS bị lộ. Chỉ sau vài phút, kẻ xấu có thể dùng key của bạn để tạo hàng loạt máy chủ đào tiền ảo và bạn nhận hoá đơn hàng nghìn đô.
- Vì vậy code chỉ ghi *tên biến* (`.env.example`), còn *giá trị thật* nằm ở `.env` chỉ có trên máy bạn. Người khác clone repo sẽ tự `Copy-Item .env.example .env` và điền key của họ.

### Nếu lỡ commit key lên GitHub

1. **Vô hiệu hoá key NGAY**: IAM → Users → `pipeline-user` → Security credentials → **Deactivate/Delete** access key, rồi tạo key mới. Đổi luôn mật khẩu database nếu bị lộ.
2. Chỉ sau đó mới xử lý repo (xoá khỏi lịch sử bằng `git filter-repo`, hoặc đơn giản là xoá repo và tạo lại). **Thu hồi key là bước bắt buộc**; chỉ xoá file thôi là không đủ.

## 6. Làm việc hằng ngày sau này

```powershell
git status
git add .
git commit -m "Mo ta ngan gon thay doi"
git push
```

Gợi ý lời nhắn commit: `Add data quality checks`, `Fix invalid discount validation`, `Update README`.

## 7. Trình bày repo cho đẹp (để dùng làm portfolio)

- Chụp ảnh dashboard Power BI → lưu vào `docs/images/` → chèn vào README bằng `![Dashboard](docs/images/page1.png)`.
- Mục **About** (bên phải trang repo): thêm mô tả một dòng và topic: `data-engineering`, `aws-s3`, `pandas`, `postgresql`, `power-bi`.
- Ghim repo lên trang profile GitHub của bạn.
