"""
TeknoMarket veritabanı erişim katmanı.
FastAPI backend bu modül üzerinden SQLite veritabanına erişir.
"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).resolve().parent / "teknomarket.db"


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def get_all_products(category: str | None = None):
    with get_connection() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM products WHERE category = ? ORDER BY id",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def get_product_by_id(product_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        return dict(row) if row else None


def get_categories():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM products ORDER BY category"
        ).fetchall()
        return [r["category"] for r in rows]


class InsufficientStockError(Exception):
    pass


class ProductNotFoundError(Exception):
    pass


def create_order(customer_id: int, items: list[dict]):
    """
    items: [{"product_id": 1, "quantity": 2}, ...]

    Stok kontrolü ve düşümü veritabanı trigger'ları tarafından
    otomatik olarak yapılır (bkz. schema.sql). Trigger tetiklenip
    RAISE(ABORT, ...) çalıştırırsa sqlite3.IntegrityError fırlatılır;
    burada bu durum anlamlı Python istisnalarına çevrilir.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO orders (customer_id, status) VALUES (?, 'PENDING')",
                (customer_id,),
            )
            order_id = cursor.lastrowid

            for item in items:
                product = cursor.execute(
                    "SELECT price FROM products WHERE id = ?",
                    (item["product_id"],),
                ).fetchone()
                if product is None:
                    raise ProductNotFoundError(
                        f"Ürün bulunamadı: {item['product_id']}"
                    )

                cursor.execute(
                    """
                    INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                    VALUES (?, ?, ?, ?)
                    """,
                    (order_id, item["product_id"], item["quantity"], product["price"]),
                )

            conn.commit()
            order = conn.execute(
                "SELECT * FROM orders WHERE id = ?", (order_id,)
            ).fetchone()
            return dict(order)

        except sqlite3.IntegrityError as e:
            conn.rollback()
            if "Yetersiz stok" in str(e):
                raise InsufficientStockError(str(e)) from e
            raise
