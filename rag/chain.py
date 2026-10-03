"""
RAG (Retrieval-Augmented Generation) sorgu zinciri.

Kullanıcının doğal dil sorusunu alır, Chroma'dan en alakalı ürün
dokümanlarını getirir (retrieval) ve Ollama üzerinde çalışan LLM'e
YALNIZCA bu dokümanları vererek cevap ürettirir. Bu sayede model
envanterde olmayan ürünler hakkında "uydurma" (halüsinasyon) yapamaz.
"""
from pathlib import Path

from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = BASE_DIR / "rag" / "chroma_db"

EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL = "llama3.2"
TOP_K = 6

SYSTEM_PROMPT = """Sen TeknoMarket adlı bir teknoloji e-ticaret sitesinin ürün uzmanı asistanısın.

KURALLAR (kesinlikle uy):
1. SADECE aşağıda "BAĞLAM" bölümünde verilen ürün bilgilerini kullanarak cevap ver.
2. Bağlamda olmayan hiçbir ürünü, özelliği veya fiyatı UYDURMA.
3. Kullanıcının sorduğu ÜRÜN TÜRÜNE (örn. laptop, ekran kartı, RAM, mouse vb.)
   dikkat et. Bağlamda o türe uymayan bir ürün varsa (örneğin kullanıcı laptop
   sorduysa ama bağlamda bir mouse da varsa), o alakasız ürünü ASLA önerme,
   sadece doğru türdeki ürünleri değerlendir.
4. Eğer bağlamdaki ürünler kullanıcının isteğini karşılamıyorsa, bunu açıkça belirt
   ("Envanterimizde bu kriterlere tam uyan bir ürün bulamadım" gibi) ve varsa en yakın
   alternatifi öner.
5. Cevaplarında ürün adını, ilgili teknik özelliği ve fiyatını mutlaka belirt.
6. Türkçe, net ve teknik olarak doğru bir dille cevap ver. Gereksiz uzatma.
7. Karşılaştırma yapılan sorularda (örn. "hangisi daha uygun") maddeler halinde gerekçelendir.

BAĞLAM (mağaza envanterinden getirilen ilgili ürünler):
{context}
"""

USER_PROMPT = "Kullanıcı sorusu: {question}"

# Basit anahtar kelime -> kategori haritası. Kullanıcının sorusunda bu
# kelimelerden biri geçiyorsa, arama sadece o kategoriyle sınırlanır.
# Bu, "en uzun pil ömürlü bilgisayar" gibi sorularda bir mouse'un
# (pil ömrü 70 saat yazdığı için) yanlışlıkla öne çıkmasını engeller.
CATEGORY_KEYWORDS = {
    "Laptop": ["laptop", "bilgisayar", "notebook", "dizüstü"],
    "Ekran Kartı": ["ekran kartı", "gpu", "grafik kartı", "graphics card"],
    "RAM": ["ram", "bellek", "memory"],
    "Depolama": ["ssd", "disk", "depolama", "hard disk", "nvme"],
    "Anakart": ["anakart", "motherboard"],
    "Aksesuar": ["mouse", "fare", "klavye", "kulaklık", "aksesuar"],
}


def detect_category(question: str) -> str | None:
    q = question.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return category
    return None


def format_docs(docs):
    return "\n\n---\n\n".join(d.page_content for d in docs)


def get_vectordb():
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    return Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
        collection_name="teknomarket_products",
    )


def get_retriever(category: str | None = None, k: int = TOP_K):
    vectordb = get_vectordb()
    search_kwargs = {"k": k}
    if category:
        search_kwargs["filter"] = {"category": category}
    return vectordb.as_retriever(search_kwargs=search_kwargs)


def build_chain(retriever):
    llm = ChatOllama(model=LLM_MODEL, temperature=0.2)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ])

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain


def ask(question: str) -> dict:
    """
    Soruyu yanıtlar ve hangi ürünlerin kaynak olarak kullanıldığını
    (source attribution) birlikte döner. Sorudaki anahtar kelimelere
    bakarak önce bir kategori tahmini yapar (örn. "laptop" geçiyorsa
    sadece Laptop kategorisinde arar), bu sayede alakasız ürünler
    (örn. bir mouse) yanlışlıkla öne çıkmaz.
    """
    category = detect_category(question)
    retriever = get_retriever(category=category)
    chain = build_chain(retriever)

    source_docs = retriever.invoke(question)
    answer = chain.invoke(question)

    sources = [
        {
            "product_id": d.metadata.get("product_id"),
            "name": d.metadata.get("name"),
            "price": d.metadata.get("price"),
        }
        for d in source_docs
    ]

    return {"answer": answer, "sources": sources, "detected_category": category}


if __name__ == "__main__":
    import sys

    question = " ".join(sys.argv[1:]) or (
        "Şarjı en uzun giden bilgisayar hangisi?"
    )
    result = ask(question)
    print("TESPİT EDİLEN KATEGORİ:", result["detected_category"])
    print("\nCEVAP:\n", result["answer"])
    print("\nKAYNAKLAR:")
    for s in result["sources"]:
        print(f"  - [{s['product_id']}] {s['name']} — {s['price']} TL")