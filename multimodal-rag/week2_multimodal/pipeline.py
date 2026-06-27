import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from week1_rag.retriever import belge_getir
from week2_multimodal.stt import ses_to_metin
from week2_multimodal.vision import goruntu_analiz
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from week1_rag.retriever import belge_getir, vektor_db
load_dotenv()

llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0,max_tokens=1000)
prompt = ChatPromptTemplate.from_template("""
<rol>
Sen bir akademik öğretmen asistanısın. Öğrencinin sorularını verilen kaynaklara dayanarak yanıtlarsın.
</rol>

<kaynak_bloklari>
Sana aşağıdaki kaynak blokları veriliyor. Her blok kendi etiketi ile başlıyor:

[DERS BELGELERİ - PDF]
{pdf_baglam}

[SES KAYDI İÇERİĞİ]
{ses_baglam}

[GÖRÜNTÜ ANALİZİ]
{goruntu_baglam}
</kaynak_bloklari>

<kesin_kurallar>
1. KAYNAK KARISTIRMA: Her bilgiyi yalnızca geldiği bloktan al. PDF bloğundaki bilgiyi ses kaydından geliyormuş gibi gösterme, tam tersi de geçerli.

2. UYDURMA YASAĞI: Hiçbir blokta olmayan bilgiyi kesinlikle yazma. Blokta yoksa "❌ Bu konuda kaynaklarda bilgi bulunamadı." yaz ve dur.

3. TEKRAR YASAĞI: Aynı cümleyi veya fikri bir kereden fazla yazma. Yazdıktan sonra bir daha yazma.

4. SES KAYDI KURALI: Ses kaydı metni ham ve gürültülü olabilir. Ham metni asla kopyalama. Anlamlı kısımları anla, temiz Türkçeyle 2-3 cümleyle özetle. Anlaşılmıyorsa: "⚠️ Ses kaydı bu konuda net bilgi içermiyor." yaz.

5. FORMÜL KURALI: Formül sorulursa önce formülü yaz, sonra her terimi tek satırda açıkla.

6. EKSİK BİLGİ KURALI: Blokta kısmi bilgi varsa: "⚠️ Kaynakta bu konuda eksik bilgi var: [bildiklerini yaz]. Kaynağı güncellemeni öneririm." yaz.
</kesin_kurallar>

<cevap_formati>
Orta uzunlukta yaz — ne çok kısa ne çok uzun. Ayrıntılı ama öz ol.

Cevabını şu yapıda ver:

[Konuya kısa giriş cümlesi]

[Açıklama — kaynak etiketleriyle]
Her bilgi bloğunun sonuna kaynak etiketi ekle:
→ (📄 PDF) veya (🎤 Ses kaydı) veya (🖼️ Görüntü)

[Varsa örnek veya özet]

---
📊 Kullanılan kaynaklar: [PDF: ✓/✗] [Ses: ✓/✗] [Görüntü: ✓/✗]
</cevap_formati>

<soru>
{question}
</soru>
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
    

def belge_getir_kaynak(soru: str, ders_id: str = None, konu_id: str = None, kaynak: str = None) -> str:
    """Belirli bir kaynak tipine göre belge getir"""
    kosullar = []
    if konu_id:
        kosullar.append({"konu_id": konu_id})
    elif ders_id:
        kosullar.append({"ders_id": ders_id})
    if kaynak:
        kosullar.append({"kaynak": kaynak})

    # ChromaDB: birden fazla koşul $and ile sarmalanmalı, tek koşul direkt verilir
    if len(kosullar) > 1:
        filtre = {"$and": kosullar}
    elif len(kosullar) == 1:
        filtre = kosullar[0]
    else:
        filtre = None

    if filtre:
        docs = vektor_db.similarity_search(soru, k=3, filter=filtre)
    else:
        docs = belge_getir(soru)

    if not docs:
        return ""

    return "\n\n".join(doc.page_content for doc in docs)

def pipeline(girdi: dict) -> str:
    goruntu_baglam = "Bu sorgu için görüntü analizi yapılmadı."
    ses_baglam = "Bu sorgu için ses kaydı analizi yapılmadı."

    if "goruntu" in girdi:
        print("Görüntü anlık analiz ediliyor...")
        goruntu_baglam = goruntu_analiz(girdi["goruntu"])

    soru = girdi.get("soru", "")
    ders_id = girdi.get("ders_id", None)
    konu_id = girdi.get("konu_id", None)
    kaynak = kaynak_belirle(soru)

    print(f"Ders ID: {ders_id} | Konu ID: {konu_id} | Kaynak: {kaynak}")

    # PDF ve ses chunk'larını ayrı ayrı getir
    pdf_docs = belge_getir_kaynak(soru, ders_id=ders_id, konu_id=konu_id, kaynak="pdf_dokuman")
    ses_docs = belge_getir_kaynak(soru, ders_id=ders_id, konu_id=konu_id, kaynak="ses_kaydi")

    if pdf_docs:
        pdf_baglam = pdf_docs
    else:
        pdf_baglam = "Bu konuda PDF kaynağında bilgi bulunamadı."

    if ses_docs:
        ses_baglam = ses_docs
    else:
        ses_baglam = "Bu konuda ses kaydında bilgi bulunamadı."

    chain = prompt | llm
    cevap = chain.invoke({
        "pdf_baglam": pdf_baglam,
        "ses_baglam": ses_baglam,
        "goruntu_baglam": goruntu_baglam,
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