# TeknoMarket — RAG Tabanlı Akıllı Teknoloji E-Ticaret Platformu

Kullanıcıların doğal dilde donanım/uyumluluk soruları sorabildiği,
cevapların yalnızca mağaza envanterindeki gerçek ürün verilerine
dayandığı bir RAG (Retrieval-Augmented Generation) e-ticaret demo projesi.

## Proje Yapısı

```
teknomarket/
├── data/
│   └── products.json          # 20 ürünlük örnek veri seti
├── database/
│   ├── schema.sql              # Tablolar, kısıtlamalar, trigger'lar
│   ├── init_db.py              # DB'yi kurar + ürünleri yükler
│   └── db.py                   # Backend'in kullandığı DB erişim katmanı
├── rag/
│   ├── ingest.py                # Ürünleri vektörleştirip Chroma'ya yazar
│   └── chain.py                 # Retrieval + LLM (Ollama) sorgu zinciri
├── backend/
│   └── main.py                  # FastAPI: /api/products, /api/orders, /api/ask
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
└── requirements.txt
```

## 1) Ön Koşullar

- Python 3.10+
- [Ollama](https://ollama.com) kurulu ve çalışıyor olmalı (kurulumdan sonra
  arka planda otomatik başlar; sistem tepsisinde Ollama simgesini görürsünüz)

Ollama modellerini çekin (PowerShell'de `&&` çalışmaz, komutları ayrı ayrı çalıştırın):
```powershell
ollama pull llama3.1
ollama pull nomic-embed-text
```

## 2) Kurulum

**Windows (PowerShell):**
```powershell
cd teknomarket
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> PowerShell "çalıştırılan komutlar devre dışı bırakıldı" hatası verirse,
> yönetici olarak bir PowerShell açıp şunu bir kere çalıştırın:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

**macOS / Linux:**
```bash
cd teknomarket
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> Sanal ortam (venv) kurmadan global Python'a kurmak isterseniz üstteki
> `venv` adımlarını atlayıp doğrudan `pip install -r requirements.txt`
> çalıştırabilirsiniz.

## 3) Veritabanını Kur

İlişkisel veritabanını (SQLite) şemadan oluşturur ve ürünleri yükler.
`schema.sql` içindeki trigger'lar stok kontrolünü ve düşümünü otomatik yapar.

```powershell
python database/init_db.py
```

## 4) Vektör Veritabanını Oluştur (RAG İndeksleme)

Ollama çalışırken (`ollama pull` adımını yapmış olmalısınız):

```powershell
python rag/ingest.py
```

Bu adım her ürünü zenginleştirilmiş bir metin chunk'ına çevirip
`nomic-embed-text` ile vektörleştirir ve `rag/chroma_db/` altına yazar.
Ürün verisini değiştirdiğinizde bu komutu tekrar çalıştırmanız gerekir.

## 5) Backend'i Başlat

```powershell
python -m uvicorn backend.main:app --reload --port 8000
```

> `uvicorn` komutu doğrudan "tanınmıyor" hatası verirse yukarıdaki gibi
> `python -m uvicorn ...` kullanın — bu, venv'in Scripts klasörü PATH'e
> eklenmemiş olsa bile her zaman çalışır.

Tarayıcıda **http://localhost:8000** adresini açın — hem ürün vitrinini
hem de sağ üstteki "AI Ürün Asistanı" panelini kullanabilirsiniz.

## 6) Hızlı Komut Satırı Testi (Frontend olmadan)

```powershell
python rag/chain.py "İş amaçlı hafif, şarjı uzun giden bir laptop öner"
```

## API Uç Noktaları

| Metod | Yol | Açıklama |
|---|---|---|
| GET | `/api/products` | Tüm ürünler (opsiyonel `?category=` filtresi) |
| GET | `/api/products/{id}` | Tek ürün detayı |
| GET | `/api/categories` | Mevcut kategoriler |
| POST | `/api/orders` | Sipariş oluşturur (trigger stok kontrolü yapar) |
| POST | `/api/ask` | RAG tabanlı doğal dil soru-cevap |

`POST /api/ask` örnek gövde:
```json
{ "question": "RTX 5070 Ti'li ve en az 16GB RAM'i olan laptoplarınız hangileri?" }
```//
Cevap `answer` (metin) ve `sources` (cevabın dayandığı ürünlerin listesi,
kaynak doğrulama/test için) içerir.

## Nasıl Halüsinasyon Önleniyor?

`rag/chain.py` içindeki sistem prompt'u modele **yalnızca retrieval ile
getirilen bağlamı kullan** talimatını verir ve bağlamda karşılık
bulunmazsa bunu açıkça belirtmesini zorunlu kılar. `/api/ask` cevabıyla
birlikte dönen `sources` listesi, üretilen cevabın gerçekten hangi
ürünlerden geldiğini doğrulamanızı sağlar — demo/test sırasında
doğruluk oranını ölçmek için bu alanı kullanabilirsiniz.

## Veritabanı Trigger'ları (schema.sql)

- `trg_check_stock_before_order_item`: Yetersiz stokla sipariş verilmesini
  `RAISE(ABORT, ...)` ile engeller.
- `trg_decrement_stock_after_order_item`: Sipariş onaylanınca stoktan düşer.
- `trg_update_order_total_after_insert`: Sipariş toplam tutarını otomatik hesaplar.
- `trg_restock_on_order_cancel`: Sipariş iptalinde stok iade edilir.

> Not: Bu proje SQLite ile geliştirilmiştir; aynı trigger mantığı
> PostgreSQL (PL/pgSQL) veya Oracle (PL/SQL) prosedürlerine
> doğrudan taşınabilir.

## Sonraki Adımlar (Geliştirme Fikirleri)

- Hibrit arama: semantik arama + anahtar kelime (BM25) birleşimi
- Uyumluluk sorguları (Soru 3 örneği) için SQL join tabanlı kural motoru
- Basit bir "faithfulness" testi: üretilen cevap, retrieve edilen chunk'larla çelişiyor mu?
- Kullanıcı hesapları ve gerçek sipariş/ödeme akışı
