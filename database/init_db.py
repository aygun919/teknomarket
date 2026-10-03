"""
Veritabanını schema.sql'den oluşturur ve data/products.json içindeki
ürünleri products tablosuna yükler.

Kullanım:
    python database/init_db.py
"""
import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "teknomarket.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
PRODUCTS_JSON_PATH = BASE_DIR / "data" / "products.json"


def init_database():
    # Var olan db dosyasını sıfırla (demo/geliştirme için)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    with open(PRODUCTS_JSON_PATH, encoding="utf-8") as f:
        products = json.load(f)

    cursor = conn.cursor()
    for p in products:
        cursor.execute(
            """
            INSERT INTO products
                (id, name, category, brand, cpu, gpu, ram_gb, ram_type,
                 storage, screen, weight_kg, battery_life_hours, price,
                 stock, description, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                p["id"], p["name"], p["category"], p["brand"], p.get("cpu"),
                p.get("gpu"), p.get("ram_gb"), p.get("ram_type"),
                p.get("storage"), p.get("screen"), p.get("weight_kg"),
                p.get("battery_life_hours"), p["price"], p["stock"],
                p.get("description"), p.get("image_url"),
            ),
        )

    # Demo müşteri
    cursor.execute(
        "INSERT INTO customers (full_name, email) VALUES (?, ?)",
        ("Demo Kullanıcı", "demo@teknomarket.com"),
    )

    conn.commit()

    count = cursor.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    print(f"✔ Veritabanı oluşturuldu: {DB_PATH}")
    print(f"✔ {count} ürün yüklendi.")
    conn.close()


if __name__ == "__main__":
    init_database()
