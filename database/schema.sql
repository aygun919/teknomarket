-- ============================================================
-- TeknoMarket İlişkisel Veritabanı Şeması
-- Not: Üretimde PostgreSQL/PL-pgSQL veya Oracle PL/SQL kullanılabilir.
-- Bu şema SQLite ile geliştirme/demo amaçlıdır; trigger mantığı
-- birebir PL/SQL prosedürlerine taşınabilecek şekilde tasarlanmıştır.
-- ============================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------
-- ÜRÜNLER TABLOSU
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id                  INTEGER PRIMARY KEY,
    name                TEXT NOT NULL,
    category            TEXT NOT NULL,
    brand               TEXT NOT NULL,
    cpu                 TEXT,
    gpu                 TEXT,
    ram_gb              INTEGER,
    ram_type            TEXT,
    storage             TEXT,
    screen              TEXT,
    weight_kg           REAL,
    battery_life_hours  INTEGER,
    price               REAL NOT NULL CHECK (price > 0),
    stock               INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    description         TEXT,
    image_url           TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);

-- ------------------------------------------------------------
-- MÜŞTERİLER TABLOSU
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name   TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- ------------------------------------------------------------
-- SİPARİŞLER TABLOSU
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id  INTEGER NOT NULL,
    status       TEXT NOT NULL DEFAULT 'PENDING'
                 CHECK (status IN ('PENDING', 'CONFIRMED', 'SHIPPED', 'CANCELLED')),
    total_amount REAL NOT NULL DEFAULT 0 CHECK (total_amount >= 0),
    created_at   TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- ------------------------------------------------------------
-- SİPARİŞ KALEMLERİ TABLOSU
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS order_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id     INTEGER NOT NULL,
    product_id   INTEGER NOT NULL,
    quantity     INTEGER NOT NULL CHECK (quantity > 0),
    unit_price   REAL NOT NULL CHECK (unit_price > 0),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- ============================================================
-- TRIGGER 1: Sipariş kalemi eklenmeden önce stok kontrolü
-- (PL/SQL BEFORE INSERT trigger mantığının SQLite karşılığı)
-- Yetersiz stok varsa işlemi RAISE(ABORT, ...) ile reddeder.
-- ============================================================
CREATE TRIGGER IF NOT EXISTS trg_check_stock_before_order_item
BEFORE INSERT ON order_items
FOR EACH ROW
BEGIN
    SELECT
        CASE
            WHEN (SELECT stock FROM products WHERE id = NEW.product_id) IS NULL
                THEN RAISE(ABORT, 'Ürün bulunamadı')
            WHEN (SELECT stock FROM products WHERE id = NEW.product_id) < NEW.quantity
                THEN RAISE(ABORT, 'Yetersiz stok: talep edilen miktar mevcut stoktan fazla')
        END;
END;

-- ============================================================
-- TRIGGER 2: Sipariş kalemi eklendikten sonra stok düşümü
-- (AFTER INSERT trigger - PL/SQL'deki stok güncelleme prosedürüne karşılık gelir)
-- ============================================================
CREATE TRIGGER IF NOT EXISTS trg_decrement_stock_after_order_item
AFTER INSERT ON order_items
FOR EACH ROW
BEGIN
    UPDATE products
    SET stock = stock - NEW.quantity
    WHERE id = NEW.product_id;
END;

-- ============================================================
-- TRIGGER 3: Sipariş toplam tutarını otomatik güncelle
-- ============================================================
CREATE TRIGGER IF NOT EXISTS trg_update_order_total_after_insert
AFTER INSERT ON order_items
FOR EACH ROW
BEGIN
    UPDATE orders
    SET total_amount = (
        SELECT COALESCE(SUM(quantity * unit_price), 0)
        FROM order_items
        WHERE order_id = NEW.order_id
    )
    WHERE id = NEW.order_id;
END;

-- ============================================================
-- TRIGGER 4: Sipariş iptal edildiğinde stok iade edilir
-- ============================================================
CREATE TRIGGER IF NOT EXISTS trg_restock_on_order_cancel
AFTER UPDATE OF status ON orders
FOR EACH ROW
WHEN NEW.status = 'CANCELLED' AND OLD.status != 'CANCELLED'
BEGIN
    UPDATE products
    SET stock = stock + (
        SELECT COALESCE(SUM(oi.quantity), 0)
        FROM order_items oi
        WHERE oi.order_id = NEW.id AND oi.product_id = products.id
    )
    WHERE id IN (SELECT product_id FROM order_items WHERE order_id = NEW.id);
END;

-- ------------------------------------------------------------
-- İndeksler (performans için)
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);
