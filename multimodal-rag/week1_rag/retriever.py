import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv

load_dotenv()

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

vektor_db = Chroma(
    persist_directory=os.path.join(os.path.dirname(__file__), "chroma_db"),
    embedding_function=embeddings
)

#similarity_search → max_marginal_relevance_search: 
# Aynı şeyi tekrar eden chunk'lar yerine çeşitlilik getirir. Tanım + örnek + uygulama gibi farklı yönleri yakalar.

retriever = vektor_db.as_retriever(search_kwargs={"k": 8})

def belge_getir(soru: str, ders_id: str = None, konu_id: str = None, kaynak: str = None) -> str:
    
    filtre_kosullari = []
    if konu_id:
        filtre_kosullari.append({"konu_id": konu_id})
    elif ders_id:
        filtre_kosullari.append({"ders_id": ders_id})
    if kaynak:
        filtre_kosullari.append({"kaynak": kaynak})
    
    if filtre_kosullari:
        filtre = {"$and": filtre_kosullari} if len(filtre_kosullari) > 1 else filtre_kosullari[0]
        docs = vektor_db.max_marginal_relevance_search( #aynı şeyleri tekrar eden chunk'lar yerine çeşitlilik getirir. Tanım + örnek + uygulama gibi farklı yönleri yakalar.
            soru,
            k=8,           # 3 → 8
            fetch_k=25,    # önce 25 aday çek, içinden çeşitli 8 tanesini seç
            filter=filtre
        )
    else:
        docs = vektor_db.max_marginal_relevance_search(soru, k=8, fetch_k=25)
    
    for doc in docs:
        print(f"--- Kaynak: {doc.metadata.get('kaynak')} | Konu: {doc.metadata.get('konu_adi')} ---")
        print(f"{doc.page_content[:100]}\n")
    
    return "\n\n".join(doc.page_content for doc in docs)
if __name__ == "__main__":
# Doğrudan "örnek" geçen chunk'ları ara
# Belirli konunun chunk'larını sil
    vektor_db.delete(where={"konu_adi": "new task"})
    vektor_db.delete(where={"konu_adi": "Gereksinim çözümleme"})