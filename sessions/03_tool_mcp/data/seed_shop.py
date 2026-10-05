"""Create data/shop.db: a small online store (customers, products, orders, order_items) for the Session 03 labs.

The data is generated, but shaped like a real shop: Vietnamese customers and cities, a fixed product catalogue,
orders from January to September 2026 with a status that depends on the order's age. A fixed random seed makes
every run produce the same database, so the numbers in the notebooks and tests do not change.

    uv run data/seed_shop.py            # writes data/shop.db next to this file
"""
import random
import unicodedata
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "shop.db"
SEED = 2026


def ascii_name(text: str) -> str:
    """'Đặng Thảo' -> 'dang thao' (for email addresses)."""
    text = text.replace("Đ", "D").replace("đ", "d")
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


FAMILY = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Ngô", "Dương"]
MIDDLE = ["Văn", "Thị", "Minh", "Thu", "Đức", "Ngọc", "Quang", "Hải", "Thanh", "Gia"]
GIVEN = ["An", "Bình", "Châu", "Dũng", "Hà", "Hiếu", "Hoa", "Huy", "Khánh", "Lan", "Linh", "Long", "Mai", "Nam",
         "Nhung", "Phúc", "Quân", "Sơn", "Tâm", "Thảo", "Trang", "Tuấn", "Việt", "Yến"]
# city -> weight (bigger cities order more)
CITIES = {"Hà Nội": 30, "TP. Hồ Chí Minh": 35, "Đà Nẵng": 10, "Hải Phòng": 7, "Cần Thơ": 6, "Huế": 5,
          "Nha Trang": 4, "Biên Hòa": 3}

PRODUCTS = {  # category -> [(name, price in VND)]
    "Books": [("Sapiens", 189_000), ("Atomic Habits", 159_000), ("Đắc Nhân Tâm", 86_000), ("Nhà Giả Kim", 79_000),
              ("Clean Code", 450_000), ("Designing Data-Intensive Applications", 690_000), ("Tuổi Trẻ Đáng Giá Bao Nhiêu", 80_000),
              ("Cà Phê Cùng Tony", 90_000), ("The Pragmatic Programmer", 520_000), ("Deep Work", 145_000)],
    "Electronics": [("Wireless Mouse", 290_000), ("Mechanical Keyboard", 1_450_000), ("USB-C Hub 7-in-1", 650_000),
                    ("27-inch Monitor", 4_990_000), ("Noise-Cancelling Headphones", 3_290_000), ("Webcam 1080p", 890_000),
                    ("Power Bank 20000mAh", 550_000), ("Bluetooth Speaker", 1_190_000), ("Smart Watch", 2_490_000),
                    ("Portable SSD 1TB", 2_190_000)],
    "Home": [("Ceramic Coffee Mug", 120_000), ("Desk Lamp LED", 450_000), ("Air Purifier", 3_590_000),
             ("Electric Kettle", 590_000), ("Rice Cooker 1.8L", 1_290_000), ("Bamboo Cutting Board", 210_000),
             ("Standing Desk", 6_490_000), ("Office Chair", 2_890_000), ("Water Bottle 1L", 180_000),
             ("Aroma Diffuser", 390_000)],
    "Toys": [("LEGO Classic Box", 990_000), ("Rubik's Cube 3x3", 95_000), ("Puzzle 1000 Pieces", 250_000),
             ("RC Car", 750_000), ("Plush Bear", 220_000), ("Board Game Catan", 1_090_000), ("Wooden Train Set", 680_000),
             ("Drawing Kit", 310_000), ("Kite", 150_000), ("Science Kit for Kids", 520_000)],
}

SCHEMA = """
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    city TEXT NOT NULL,
    created_at TEXT NOT NULL            -- ISO date the account was created
);
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,             -- Books | Electronics | Home | Toys
    price INTEGER NOT NULL              -- current price in VND
);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    status TEXT NOT NULL CHECK (status IN ('pending', 'paid', 'shipped', 'delivered', 'cancelled')),
    created_at TEXT NOT NULL            -- ISO timestamp of the order
);
CREATE TABLE order_items (
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price INTEGER NOT NULL,        -- price paid per unit in VND (may differ from products.price)
    PRIMARY KEY (order_id, product_id)
);
"""

START, END = datetime(2026, 1, 1), datetime(2026, 9, 30, 23, 59)


def status_for(created: datetime, rng: random.Random) -> str:
    """Recent orders are still in progress; older ones are mostly delivered. About 5 % are cancelled."""
    if rng.random() < 0.05:
        return "cancelled"
    age = (END - created).days
    if age < 3:
        return rng.choice(["pending", "paid"])
    if age < 10:
        return rng.choice(["paid", "shipped", "shipped", "delivered"])
    return "delivered"


def build(db_path: Path = DB_PATH, n_customers: int = 200, n_orders: int = 1500) -> dict:
    rng = random.Random(SEED)
    db_path.unlink(missing_ok=True)
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)

    customers = []
    for cid in range(1, n_customers + 1):
        name = f"{rng.choice(FAMILY)} {rng.choice(MIDDLE)} {rng.choice(GIVEN)}"
        local = ascii_name(name.split()[-1]) + "." + ascii_name(name.split()[0])
        email = f"{local}{cid}@example.com"  # example.com: never a real mailbox
        city = rng.choices(list(CITIES), weights=CITIES.values())[0]
        created = START - timedelta(days=rng.randint(0, 700))
        customers.append((cid, name, email, city, created.date().isoformat()))
    con.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?)", customers)

    products, pid = [], 0
    for category, items in PRODUCTS.items():
        for name, price in items:
            pid += 1
            products.append((pid, name, category, price))
    con.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", products)

    # a few loyal customers order much more often than the rest
    weights = [rng.paretovariate(1.5) for _ in customers]
    span = (END - START).total_seconds()
    # more orders later in the year (the shop grows); ids follow time, like a real auto-increment key
    times = sorted(START + timedelta(seconds=span * rng.random() ** 0.8) for _ in range(n_orders))
    orders, items = [], []
    for oid, created in enumerate(times, start=1):
        customer = rng.choices(customers, weights=weights)[0][0]
        orders.append((oid, customer, status_for(created, rng), created.isoformat(timespec="seconds")))
        for product in rng.sample(products, k=rng.choices([1, 2, 3, 4], weights=[50, 30, 15, 5])[0]):
            discount = rng.choice([1.0, 1.0, 1.0, 0.9, 0.85])  # sometimes sold on promotion
            items.append((oid, product[0], rng.choices([1, 2, 3], weights=[75, 20, 5])[0], int(product[3] * discount)))
    con.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", orders)
    con.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?)", items)
    con.commit()
    counts = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
              for t in ("customers", "products", "orders", "order_items")}
    con.close()
    return counts


if __name__ == "__main__":
    print(DB_PATH, build())
