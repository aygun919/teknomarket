"""
Ürün verilerini metin parçalarına (chunk) dönüştürüp Ollama embedding
modeli ile vektörleştirerek Chroma vektör veritabanına yazar.

Ön koşul:
    - Ollama kurulu ve çalışıyor olmalı (https://ollama.com)
    - Embedding modeli çekilmiş olmalı:  ollama pull nomic-embed-text

Kullanım:
    python rag/ingest.py
"""
import json
from pathlib import Path

from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

BASE_DIR = Path(__file__).resolve().parent.parent
PRODUCTS_JSON_PATH = BASE_DIR / "data" / "products.json"
CHROMA_DIR = BASE_DIR / "rag" / "chroma_db"

EMBEDDING_MODEL = "nomic-embed-text"


def build_product_document(p: dict) -> Document:
    """
    Her ürünü tek bir chunk halinde, RAG'in doğal dil sorularını
    (RAM, GPU, ağırlık, pil ömrü vb.) yakalayabileceği şekilde
    zenginleştirilmiş bir metne dönüştürür.
    """
    specs = []
    if p.get("cpu"):
        specs.append(f"İşlemci (CPU): {p['cpu']}")
    if p.get("gpu"):
        specs.append(f"Ekran kartı (GPU): {p['gpu']}")
    if p.get("ram_gb"):
        specs.append(f"RAM: {p['ram_gb']} GB, tip: {p.get('ram_type', 'belirtilmemiş')}")
    if p.get("storage"):
        specs.append(f"Depolama: {p['storage']}")
    if p.get("screen"):
        specs.append(f"Ekran: {p['screen']}")
    if p.get("weight_kg"):
        specs.append(f"Ağırlık: {p['weight_kg']} kg")
    if p.get("battery_life_hours"):
        specs.append(f"Pil ömrü: yaklaşık {p['battery_life_hours']} saat")

    content = (
        f"Ürün adı: {p['name']}\n"
        f"Kategori: {p['category']}\n"
        f"Marka: {p['brand']}\n"
        f"Fiyat: {p['price']} TL\n"
        f"Stok durumu: {p['stock']} adet\n"
        f"Teknik özellikler:\n- " + "\n- ".join(specs) + "\n"
        f"Açıklama: {p.get('description', '')}"
    )

    return Document(
        page_content=content,
        metadata={
            "product_id": p["id"],
            "name": p["name"],
            "category": p["category"],
            "brand": p["brand"],
            "price": p["price"],
        },
    )


def ingest():
    with open(PRODUCTS_JSON_PATH, encoding="utf-8") as f:
        products = json.load(f)

    documents = [build_product_document(p) for p in products]
    print(f"{len(documents)} ürün dokümanı hazırlandı.")

    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)

    Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
        collection_name="teknomarket_products",
    )
    print(f"✔ Vektör veritabanı oluşturuldu: {CHROMA_DIR}")


if __name__ == "__main__":
    ingest()
