import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from week1_rag.retriever import vektor_db

sonuc = vektor_db.get(include=["metadatas", "documents"])
for i, meta in enumerate(sonuc["metadatas"]):
    if meta.get("kaynak") == "goruntu":
        print(f"Dosya: {meta.get('dosya')} | Konu: {meta.get('konu_adi')}")
        print(f"İçerik: {sonuc['documents'][i][:100]}\n")


silinecek = [sonuc["ids"][i] for i, m in enumerate(sonuc["metadatas"]) 
             if m.get("dosya") == "indir (1).png"]
if silinecek:
    vektor_db.delete(ids=silinecek)
    print(f"{len(silinecek)} chunk silindi")