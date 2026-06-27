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

llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0,max_tokens=1000)
prompt = ChatPromptTemplate.from_template("""
<rol>
Sen bir akademik öğretmen asistanısın. Görevin, öğrencinin sorusunu YALNIZCA aşağıdaki kaynak bloklarına dayanarak yanıtlamak. Kaynak dışına çıkmazsın.
</rol>

<konusma_gecmisi>
Aşağıda önceki konuşma var. Öğrencinin yeni sorusu "bunu", "peki ya", "neden öyle" gibi önceki cevaba atıfsa, bağlamı buradan çöz. Geçmiş boşsa yok say.
{history}
</konusma_gecmisi>

<kaynak_bloklari>
[DERS BELGELERİ - PDF]
{pdf_baglam}

[SES KAYDI İÇERİĞİ]
{ses_baglam}

[GÖRÜNTÜ ANALİZİ]
{goruntu_baglam}
</kaynak_bloklari>

<once_dusun>
Cevap yazmadan önce kendine sor (bunları YAZMA, sadece düşün):
- Öğrenci tek bir spesifik şey mi soruyor, yoksa konunun genel özetini mi istiyor?
- Cevap hangi blokta? Birden fazla blokta mı? Hiçbirinde yoksa uydurma.
- Genel soruysa: ilgili bloktaki TÜM parçaları birleştirip bütüncül bir cevap kur, tek bir cümleye yapışma.
- Spesifik soruysa: sadece sorulan noktaya odaklan, fazlasını ekleme.
</once_dusun>

<kesin_kurallar>
1. TOPRAKLAMA: Her cümlenin dayanağı bir blokta olmalı. Blokta yoksa yazma. Genel kültüründen, tahminden ya da "muhtemelen"den asla bilgi ekleme.
2. KAYNAK KARIŞTIRMA YOK: Her bilgiyi yalnızca geldiği bloktan al ve etiketle. PDF bilgisini ses kaydından geliyormuş gibi gösterme.
3. UYDURMA YASAĞI: Hiçbir blokta olmayan bilgi için "❌ Bu konuda kaynaklarda bilgi bulunamadı." yaz ve dur. Bilgi yoksa boşluğu doldurma.
4. TEKRAR YASAĞI: Aynı fikri/cümleyi iki kez yazma.
5. SES KAYDI: Ham ve gürültülü olabilir. Kopyalama; anlamlı kısmı 2-3 cümleyle temiz Türkçeyle özetle. Anlaşılmıyorsa "⚠️ Ses kaydı bu konuda net bilgi içermiyor." yaz.
6. FORMÜL: Önce formülü yaz, sonra her terimi tek satırda açıkla.
7. EKSİK BİLGİ: Blokta kısmi bilgi varsa "⚠️ Kaynakta eksik bilgi var: [bildiklerin]. Kaynağı güncellemeni öneririm." yaz — ama elindeki kısmı tam ver.
</kesin_kurallar>

<cevap_formati>
Orta uzunluk. Spesifik soruda kısa ve nokta atışı; genel soruda kapsayıcı ama özlü.

[Konuya kısa giriş]

[Açıklama — her bilgi bloğunun sonuna etiket: → (📄 PDF) / (🎤 Ses kaydı) / (🖼️ Görüntü)]

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

def pipeline(girdi: dict, gecmis: list = None) -> str:
    gecmis = gecmis or []
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
        # Son 3 tur (6 satır) prompt'a girsin; tüm geçmiş çağıran tarafta kalır.
        # gecmis boşken "".join([]) == "" → {history} boş gider, KeyError olmaz.
        "history": "\n".join(gecmis[-6:]),
        "pdf_baglam": pdf_baglam,
        "ses_baglam": ses_baglam,
        "goruntu_baglam": goruntu_baglam,
        "question": soru
    })

    # Bu turu geçmişe ekle (liste mutable; çağıran taraftaki session_state listesi
    # de aynı nesne olduğundan otomatik güncellenir).
    gecmis.append(f"Öğrenci: {soru}")
    gecmis.append(f"Asistan: {cevap.content}")

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