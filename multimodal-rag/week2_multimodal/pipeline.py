import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from week1_rag.retriever import belge_getir
from week2_multimodal.stt import ses_to_metin
from week2_multimodal.vision import goruntu_analiz
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0,max_tokens=1000)

prompt = ChatPromptTemplate.from_template("""
Sen bir akademik asistansın. Aşağıdaki kurallara kesinlikle uy:

1. Bağlamda konuyla ilgili herhangi bir bilgi varsa — dolaylı bile olsa — onu kullanarak cevap ver.
2. Sadece bağlamda hiç ilgili bilgi yoksa "Bu konuda bilgim yok" de.
3. Bağlamdaki bilgi eksik veya dolaylıysa, bildiklerini söyle ve "Bağlamda daha fazla detay yok" de.
4. Hangi kaynaktan cevap verdiğini belirt — ses kaydı mı, PDF mi, görüntü mü.

Bağlam:
{context}

Soru: {question}
""")

def kaynak_belirle(soru: str) -> str:
    """Soruya göre hangi kaynağa bakılacağını belirle"""
    soru_lower = soru.lower()
    
    if any(k in soru_lower for k in ["ses", "kayıt", "derste", "hoca", "anlattı", "söyledi"]):
        return "ses_kaydi"
    elif any(k in soru_lower for k in ["pdf", "belgede", "dokümanda", "notlarda", "kitapta"]):
        return "pdf_dokuman"
    elif any(k in soru_lower for k in ["görüntü", "resim", "görselde", "fotoğraf", "şekil"]):
        return "goruntu"
    else:
        return None  # filtre yok, hepsine bak

def pipeline(girdi: dict) -> str:
    goruntu_icerigi = ""

    if "goruntu" in girdi:
        print("Görüntü anlık analiz ediliyor...")
        goruntu_icerigi = goruntu_analiz(girdi["goruntu"])

    soru = girdi.get("soru", "")
    ders_id = girdi.get("ders_id", None)
    konu_id = girdi.get("konu_id", None)  # ← ekle

    kaynak = kaynak_belirle(soru)
    print(f"Ders ID: {ders_id} | Konu ID: {konu_id} | Kaynak: {kaynak}")

    baglam = belge_getir(soru, ders_id=ders_id, konu_id=konu_id, kaynak=kaynak)

    if goruntu_icerigi:
        tam_baglam = f"--- GÖRÜNTÜ ANALİZİ ---\n{goruntu_icerigi}\n\n--- DERS BELGELERİ ---\n{baglam}"
    else:
        tam_baglam = f"--- DERS BELGELERİ ---\n{baglam}"

    chain = prompt | llm
    cevap = chain.invoke({
        "context": tam_baglam,
        "question": soru
    })

    return cevap.content

if __name__ == "__main__":
    print("=" * 50)
    print("TEST 1: Sadece metin sorusu")
    print("=" * 50)
    cevap = pipeline({"soru": "8086 mikroişlemcisinde segment registers ne işe yarar?"})
    print(f"\nCevap: {cevap}")

    print("\n" + "=" * 50)
    print("TEST 2: Görüntü + soru")
    print("=" * 50)
    goruntu_yolu = "C:\\Users\\merve\\Desktop\\miuul_generative_ai\\Multimodal Assistant\\multimodal-rag\\week2_multimodal\\data\\test.png"
    if os.path.exists(goruntu_yolu):
        cevap = pipeline({
            "goruntu": goruntu_yolu,
            "soru": "Bu görseli açıkla ve notlarımla ilgili ne söyleyebilirsin?"
        })
        print(f"\nCevap: {cevap}")

    print("\n" + "=" * 50)
    print("TEST 3: Ses + soru")
    print("=" * 50)
    ses_yolu = "C:\\Users\\merve\\Desktop\\miuul_generative_ai\\Multimodal Assistant\\multimodal-rag\\week2_multimodal\\data\\test.mp4"
    if os.path.exists(ses_yolu):
        cevap = pipeline({
            "ses": ses_yolu,
            "soru": "Ses kaydındaki konuyu özetle"
        })
        print(f"\nCevap: {cevap}")