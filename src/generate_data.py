import pandas as pd
import random
from datetime import datetime, timedelta
import os
import time

# Cấu hình đường dẫn
RAW_DATA_DIR = os.path.join("data", "raw")
OUTPUT_FILE = os.path.join(RAW_DATA_DIR, "orders.csv")

# Danh mục sản phẩm (Đa dạng hơn)
PRODUCTS = [
    {"id": "P001", "name": "Laptop ASUS ROG", "category": "Electronics", "price": 35000000},
    {"id": "P002", "name": "MacBook Pro M3", "category": "Electronics", "price": 45000000},
    {"id": "P003", "name": "Mouse Logitech MX Master", "category": "Accessories", "price": 2500000},
    {"id": "P004", "name": "Keychron K8 Pro", "category": "Accessories", "price": 2200000},
    {"id": "P005", "name": "iPhone 15 Pro Max", "category": "Mobile", "price": 30000000},
    {"id": "P006", "name": "Samsung Galaxy S24 Ultra", "category": "Mobile", "price": 28000000},
    {"id": "P007", "name": "Sony WH-1000XM5", "category": "Audio", "price": 7500000},
    {"id": "P008", "name": "AirPods Pro 2", "category": "Audio", "price": 6000000},
    {"id": "P009", "name": "iPad Pro 11", "category": "Tablet", "price": 22000000},
    {"id": "P010", "name": "Dell UltraSharp 27", "category": "Electronics", "price": 12000000}
]

# Tỉ lệ phân phối thực tế (TP.HCM và Hà Nội chiếm đa số)
CITIES = ["Ho Chi Minh", "Ha Noi", "Da Nang", "Can Tho", "Thu Dau Mot", "Hai Phong", "Bien Hoa"]
CITY_WEIGHTS = [0.4, 0.3, 0.1, 0.05, 0.05, 0.05, 0.05] 

PAYMENT_METHODS = ["Banking", "Credit Card", "Cash on Delivery", "Momo", "ZaloPay"]
STATUSES = ["Completed", "Pending", "Cancelled", "Refunded"]
DEVICE_TYPES = ["Mobile App", "Mobile Web", "Desktop Web", "Tablet"]
PROMO_CODES = ["FREESHIP", "MEGA_SALE", "NEW_USER", "VIP10", None, None, None] # 3/7 cơ hội không có mã

def generate_orders(num_records=500000):
    start_time = time.time()
    print(f"Bắt đầu tạo {num_records} records dữ liệu (Cấp độ Đồ án)...")
    
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    
    data = []
    start_date = datetime(2025, 1, 1)
    
    # Pre-generate dates to simulate seasonal spikes (e.g., Year end sales)
    dates = []
    for _ in range(num_records):
        # Tạo hiệu ứng dồn đơn hàng vào cuối năm
        if random.random() < 0.3:
            random_days = random.randint(300, 365) # Tháng 11, 12
        else:
            random_days = random.randint(0, 299)
        dates.append((start_date + timedelta(days=random_days)).strftime("%Y-%m-%d"))

    # Sinh dữ liệu hàng loạt
    for i in range(1, num_records + 1):
        order_id = f"ORD{i:07d}"
        customer_id = f"CUS{random.randint(1, 15000):05d}"
        
        product = random.choice(PRODUCTS)
        quantity = random.choices([1, 2, 3, 4, 5], weights=[0.6, 0.2, 0.1, 0.05, 0.05])[0]
        discount = random.choices([0, 0.05, 0.1, 0.15, 0.2], weights=[0.5, 0.2, 0.15, 0.1, 0.05])[0]
        shipping_fee = random.choices([0, 15000, 30000, 50000], weights=[0.4, 0.3, 0.2, 0.1])[0]
        
        record = {
            "order_id": order_id,
            "customer_id": customer_id,
            "order_date": dates[i-1],
            "product_id": product["id"],
            "product_name": product["name"],
            "category": product["category"],
            "quantity": quantity,
            "unit_price": product["price"],
            "discount": discount,
            "shipping_fee": shipping_fee,
            "promo_code": random.choice(PROMO_CODES),
            "device_type": random.choices(DEVICE_TYPES, weights=[0.5, 0.2, 0.2, 0.1])[0],
            "payment_method": random.choice(PAYMENT_METHODS),
            "city": random.choices(CITIES, weights=CITY_WEIGHTS)[0],
            "status": random.choices(STATUSES, weights=[0.8, 0.1, 0.08, 0.02])[0]
        }
        
      
        # INJECT LỖI ĐỂ KIỂM TRA DATA QUALITY (Chiếm khoảng 3%)
       
        rand_val = random.random()
        
        if rand_val < 0.005:   # 0.5% Mất Customer ID
            record["customer_id"] = None
        elif rand_val < 0.01:  # 0.5% Số lượng âm
            record["quantity"] = random.randint(-5, -1)
        elif rand_val < 0.015: # 0.5% Giá âm hoặc 0
            record["unit_price"] = 0
        elif rand_val < 0.02:  # 0.5% Trạng thái rác
            record["status"] = "System_Error"
        elif rand_val < 0.025: # 0.5% Nhập sai Discount (> 100%)
            record["discount"] = random.uniform(1.1, 2.0)
        elif rand_val < 0.03:  # 0.5% Sai định dạng ngày
            record["order_date"] = "2025/13/45" 
            
        data.append(record)
        
    df = pd.DataFrame(data)
    
    # Tạo duplicate (Trùng lặp hóa đơn - Lỗi do hệ thống retry)
    print("Đang cấy dữ liệu trùng lặp (Duplicates)...")
    duplicates = df.sample(n=5000) # Cố tình duplicate 5000 dòng
    df = pd.concat([df, duplicates], ignore_index=True)
    
    # Xáo trộn dữ liệu
    df = df.sample(frac=1).reset_index(drop=True)
    
    # Lưu ra CSV
    print("Đang lưu ra file CSV (Quá trình này có thể mất 5-10 giây)...")
    df.to_csv(OUTPUT_FILE, index=False)
    
    end_time = time.time()
    print("="*50)
    print(f"HOÀN THÀNH TẠO DỮ LIỆU!")
    print(f"- Đường dẫn: {OUTPUT_FILE}")
    print(f"- Tổng số dòng: {len(df):,}")
    print(f"- Dung lượng file ước tính: {os.path.getsize(OUTPUT_FILE) / (1024*1024):.2f} MB")
    print(f"- Thời gian chạy: {end_time - start_time:.2f} giây")
    print("="*50)

if __name__ == "__main__":
    generate_orders(500000) # Đổi thành 500k
