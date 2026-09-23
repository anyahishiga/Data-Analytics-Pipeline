```python
import csv
import random
import os
from datetime import datetime, timedelta


DATA_DIR = "data/raw"
OUTPUT_FILE = os.path.join(DATA_DIR, "orders.csv")

PRODUCTS = [
    {
        "id": "P001",
        "name": "Laptop ASUS",
        "category": "Electronics",
        "price": 18000000
    },
    {
        "id": "P002",
        "name": "iPhone 15",
        "category": "Electronics",
        "price": 22000000
    },
    {
        "id": "P003",
        "name": "Samsung Galaxy",
        "category": "Electronics",
        "price": 15000000
    },
    {
        "id": "P004",
        "name": "Wireless Mouse",
        "category": "Accessories",
        "price": 450000
    },
    {
        "id": "P005",
        "name": "Mechanical Keyboard",
        "category": "Accessories",
        "price": 1200000
    },
    {
        "id": "P006",
        "name": "Headphones",
        "category": "Accessories",
        "price": 1800000
    },
    {
        "id": "P007",
        "name": "Backpack",
        "category": "Fashion",
        "price": 650000
    },
    {
        "id": "P008",
        "name": "Running Shoes",
        "category": "Fashion",
        "price": 1500000
    },
    {
        "id": "P009",
        "name": "T-Shirt",
        "category": "Fashion",
        "price": 350000
    },
    {
        "id": "P010",
        "name": "Coffee Machine",
        "category": "Home",
        "price": 3200000
    }
]

CITIES = [
    "Ho Chi Minh City",
    "Thu Dau Mot",
    "Hanoi",
    "Da Nang",
    "Can Tho",
    "Hai Phong"
]

PAYMENT_METHODS = [
    "Cash",
    "Banking",
    "Credit Card",
    "E-Wallet"
]

ORDER_STATUS = [
    "Completed",
    "Completed",
    "Completed",
    "Pending",
    "Cancelled"
]


def generate_order(order_number):
    product = random.choice(PRODUCTS)

    start_date = datetime(2026, 1, 1)
    order_date = start_date + timedelta(
        days=random.randint(0, 364)
    )

    quantity = random.randint(1, 5)

    discount = random.choice([
        0,
        0,
        0.05,
        0.10,
        0.15
    ])

    return {
        "order_id": f"ORD{order_number:06d}",
        "customer_id": f"CUS{random.randint(1, 2000):05d}",
        "order_date": order_date.strftime("%Y-%m-%d"),
        "product_id": product["id"],
        "product_name": product["name"],
        "category": product["category"],
        "quantity": quantity,
        "unit_price": product["price"],
        "discount": discount,
        "payment_method": random.choice(PAYMENT_METHODS),
        "city": random.choice(CITIES),
        "status": random.choice(ORDER_STATUS)
    }


def create_dataset(number_of_orders=10000):
    orders = []

    for i in range(1, number_of_orders + 1):
        orders.append(generate_order(i))

    return orders


def save_to_csv(orders):
    os.makedirs(DATA_DIR, exist_ok=True)

    fieldnames = [
        "order_id",
        "customer_id",
        "order_date",
        "product_id",
        "product_name",
        "category",
        "quantity",
        "unit_price",
        "discount",
        "payment_method",
        "city",
        "status"
    ]

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(orders)


def main():
    print("Creating e-commerce dataset...")

    orders = create_dataset(10000)

    save_to_csv(orders)

    print(f"Created {len(orders)} orders.")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
```
