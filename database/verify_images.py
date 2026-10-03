"""
Ürün görsellerinin doğru dosya adlarıyla eşleştiğini kontrol eder.

- products.json'daki her ürün için beklenen görsel dosyasının
  frontend/images/ altında var olup olmadığını kontrol eder.
- frontend/images/ altında olup hiçbir ürüne karşılık gelmeyen
  "yetim" dosyaları da listeler.

Kullanım:
    python database/verify_images.py
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PRODUCTS_JSON_PATH = BASE_DIR / "data" / "products.json"
IMAGES_DIR = BASE_DIR / "frontend" / "images"


def verify_images():
    with open(PRODUCTS_JSON_PATH, encoding="utf-8") as f:
        products = json.load(f)

    missing = []
    ok = []

    for p in products:
        image_url = p.get("image_url", "")
        filename = image_url.split("/")[-1] if image_url else None
        file_path = IMAGES_DIR / filename if filename else None

        if not filename or not file_path.exists():
            missing.append((p["id"], p["name"], filename))
        else:
            ok.append((p["id"], p["name"], filename))

    expected_filenames = {
        p.get("image_url", "").split("/")[-1] for p in products if p.get("image_url")
    }
    existing_files = {f.name for f in IMAGES_DIR.glob("*") if f.is_file() and f.name != ".gitkeep"}
    orphan_files = existing_files - expected_filenames

    print(f"✔ Görseli mevcut: {len(ok)} / {len(products)} ürün\n")
    for pid, name, fname in ok:
        print(f"  [{pid:>2}] {name}  ->  {fname}")

    if missing:
        print(f"\n✘ Görseli EKSİK: {len(missing)} ürün")
        for pid, name, fname in missing:
            print(f"  [{pid:>2}] {name}  ->  beklenen dosya: {fname}")
    else:
        print("\n✔ Eksik görsel yok.")

    if orphan_files:
        print(f"\n⚠ Hiçbir ürüne bağlı olmayan (yetim) dosyalar: {len(orphan_files)}")
        for f in sorted(orphan_files):
            print(f"  - {f}  (muhtemelen yanlış isimlendirilmiş bir görsel)")
    else:
        print("✔ Sahipsiz/yetim dosya yok.")


if __name__ == "__main__":
    verify_images()