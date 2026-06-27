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

retriever = vektor_db.as_retriever(search_kwargs={"k": 6})
def belge_getir(soru: str, ders_id: str = None, konu_id: str = None, kaynak: str = None) -> str:
    
    filtre_kosullari = []
    if konu_id:
        filtre_kosullari.append({"konu_id": konu_id})  # konu seçiliyse öncelikli filtre
    elif ders_id:
        filtre_kosullari.append({"ders_id": ders_id})  # konu yoksa derse göre filtrele
    if kaynak:
        filtre_kosullari.append({"kaynak": kaynak})
    
    if filtre_kosullari:
        # Multiple conditions need $and operator for Chroma
        filtre = {"$and": filtre_kosullari} if len(filtre_kosullari) > 1 else filtre_kosullari[0]
        docs = vektor_db.similarity_search(
            soru,
            k=3,
            filter=filtre
        )
    else:
        docs = retriever.invoke(soru)
    
    for doc in docs:
        print(f"--- Kaynak: {doc.metadata.get('kaynak')} | Konu: {doc.metadata.get('konu_adi')} ---")
        print(f"{doc.page_content[:100]}\n")
    
    return "\n\n".join(doc.page_content for doc in docs)

if __name__ == "__main__":
    test_soru = "8086 mikroişlemcisinde segment registers ne işe yarar?"
    print(f"Soru: {test_soru}")
    print(f"\nBulunan belgeler:\n{belge_getir(test_soru)}")