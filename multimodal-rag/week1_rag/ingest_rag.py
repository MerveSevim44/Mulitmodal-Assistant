import os
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from week2_multimodal.stt import ses_to_metin
from langchain_core.documents import Document
from pypdf import PdfReader


load_dotenv()

from langchain_core.documents import Document
belgeler = [
    Document(
        page_content="LangChain, dil modelleriyle uygulama geliştirmeyi kolaylaştıran bir Python kütüphanesidir.",
        metadata={"kaynak": "ders_notu", "ders": "NLP", "tarih": "2024-04-14"}
    ),
    Document(
        page_content="ChromaDB, metinleri vektör olarak saklayan ve benzerlik araması yapan bir veritabanıdır.",
        metadata={"kaynak": "ders_notu", "ders": "Veritabanı", "tarih": "2024-04-14"}
    ),
    Document(
        page_content="RAG sistemi, önce ilgili belgeleri bulur, sonra LLM'e bağlam olarak verir.",
        metadata={"kaynak": "ses_kaydi", "ders": "NLP", "dakika": 15}
    ),
]

# Metinleri parçalara böl (metadata'yı koru)
splitter = RecursiveCharacterTextSplitter(
    chunk_size=200,
    chunk_overlap=20
)
parcalar = splitter.split_documents(belgeler)
print(f"{len(parcalar)} parça oluşturuldu")

# Parçaları göster
for i, p in enumerate(parcalar):
    print(f"Parça {i+1}: {p.page_content}")
    print(f"Metadata: {p.metadata}")
    print("---")

# Embedding modeli (ilk çalıştırmada ~90MB indirir)
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# ChromaDB'ye kaydet
vektor_db = Chroma.from_documents(
    documents=parcalar,
    embedding=embeddings,
    persist_directory=os.path.join(os.path.dirname(__file__), "chroma_db")
)

print("Belgeler ChromaDB'ye kaydedildi!")
print(f"Toplam vektör sayısı: {vektor_db._collection.count()}")

def ses_yukle(dosya_yolu: str, ders_adi: str, ders_id: str, konu_adi: str = None, konu_id: str = None) -> None:
    """Ses dosyasını metne çevirip ChromaDB'ye kaydeder"""
    sonuc = ses_to_metin(dosya_yolu)
    tam_metin = sonuc["tam_metin"]
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    
    parcalar = splitter.create_documents(
        texts=[tam_metin],
        metadatas=[{
            "kaynak": "ses_kaydi",       # ← düzeltildi
            "ders_id": ders_id,
            "ders_adi": ders_adi,
            "konu_id": konu_id or "",
            "konu_adi": konu_adi or "",
            "tarih": datetime.now().strftime("%Y-%m-%d"),
            "dosya": os.path.basename(dosya_yolu)
        }]
    )
    
    vektor_db.add_documents(parcalar)
    print(f"Toplam {len(parcalar)} chunk kaydedildi!")


def pdf_yukle(dosya_yolu: str, ders_adi: str, ders_id: str, konu_adi: str = None, konu_id: str = None) -> None:
    reader = PdfReader(dosya_yolu)
    print(f"Toplam sayfa: {len(reader.pages)}")
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = []
    
    for i, sayfa in enumerate(reader.pages):
        metin = sayfa.extract_text()
        if not metin or len(metin) < 100:
            continue
        
        parcalar = splitter.create_documents(
            texts=[metin],
            metadatas=[{
                "kaynak": "pdf_dokuman",
                "ders_id": ders_id,
                "ders_adi": ders_adi,
                "konu_id": konu_id or "",
                "konu_adi": konu_adi or "",
                "tarih": datetime.now().strftime("%Y-%m-%d"),
                "sayfa_numarasi": i + 1,
                "dosya": os.path.basename(dosya_yolu)
            }]
        )
        docs.extend(parcalar)
    
    vektor_db.add_documents(docs)
    print(f"Toplam {len(docs)} chunk kaydedildi!")


def goruntu_yukle(dosya_yolu: str, ders_adi: str, ders_id: str, konu_adi: str = None, konu_id: str = None) -> None:
    from week2_multimodal.vision import goruntu_analiz
    
    print(f"Görüntü analiz ediliyor: {dosya_yolu}")
    metin = goruntu_analiz(dosya_yolu)
    
    doc = Document(
        page_content=metin,
        metadata={
            "kaynak": "goruntu",
            "ders_id": ders_id,
            "ders_adi": ders_adi,
            "konu_id": konu_id or "",
            "konu_adi": konu_adi or "",
            "tarih": datetime.now().strftime("%Y-%m-%d"),
            "dosya": os.path.basename(dosya_yolu)
        }
    )
    vektor_db.add_documents([doc])
    print("Görüntü ChromaDB'ye kaydedildi!")




if __name__ == "__main__":
    # Önce mevcut belgeleri yükle
    # Sonra ses dosyasını yükle
    ses_yukle(
        "C:\\Users\\merve\\Desktop\\miuul_generative_ai\\Multimodal Assistant\\multimodal-rag\\week2_multimodal\\data\\test.mp4",
        ders="Yapay Zeka"
    )
    pdf_yukle(
        "C:\\Users\\merve\\Desktop\\miuul_generative_ai\\Multimodal Assistant\\multimodal-rag\\week2_multimodal\\data\\ders_notu.pdf",
    ders="mikroişlem"  # kendi ders adını yaz
    )