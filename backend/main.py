"""
TeknoMarket FastAPI Backend

Çalıştırma:
    uvicorn backend.main:app --reload --port 8000

Ardından tarayıcıda http://localhost:8000 adresini aç.
"""
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from database import db  # noqa: E402

app = FastAPI(title="TeknoMarket API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------
# Pydantic modelleri
# ---------------------------------------------------------------
class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderIn(BaseModel):
    customer_id: int = 1
    items: list[OrderItemIn]


class AskIn(BaseModel):
    question: str = Field(min_length=3)


# ---------------------------------------------------------------
# Ürün Endpoint'leri
# ---------------------------------------------------------------
@app.get("/api/products")
def list_products(category: Optional[str] = None):
    return db.get_all_products(category=category)


@app.get("/api/categories")
def list_categories():
    return db.get_categories()


@app.get("/api/products/{product_id}")
def get_product(product_id: int):
    product = db.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    return product


# ---------------------------------------------------------------
# Sipariş Endpoint'i
# ---------------------------------------------------------------
@app.post("/api/orders")
def create_order(order: OrderIn):
    try:
        result = db.create_order(
            customer_id=order.customer_id,
            items=[item.model_dump() for item in order.items],
        )
        return result
    except db.InsufficientStockError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except db.ProductNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------
# RAG Soru-Cevap Endpoint'i
# ---------------------------------------------------------------
@app.post("/api/ask")
def ask_question(payload: AskIn):
    """
    Kullanıcının doğal dil sorusunu RAG zincirine gönderir.
    NOT: Bu endpoint'in çalışması için Ollama'nın yerel olarak
    çalışıyor ve gerekli modellerin çekilmiş olması gerekir
    (bkz. README.md).
    """
    try:
        from rag.chain import ask  # gecikmeli import: Ollama yoksa API ayakta kalabilsin
        result = ask(payload.question)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=(
                "RAG asistanına şu anda ulaşılamıyor. Ollama'nın çalıştığından "
                f"ve modellerin çekildiğinden emin olun. Detay: {e}"
            ),
        )


# ---------------------------------------------------------------
# Frontend'i sun (statik dosyalar)
# ---------------------------------------------------------------
FRONTEND_DIR = BASE_DIR / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")
