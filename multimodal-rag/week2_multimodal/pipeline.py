import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
Sen bir belge/görsel/ses analiz asistanısın. Öğrencinin sağladığı PDF, görüntü ve ses
kaynaklarını analiz eder, sorularını yanıtlarsın. Cevaplarını HER ZAMAN iki bilgi
katmanına ayırırsın:

📎 KAYNAK  → yalnızca sağlanan kaynaklarda DOĞRUDAN yer alan bilgi.
🧠 GENEL BİLGİ → kaynakta yazmayan ama konunun anlaşılmasına/değerlendirilmesine
                 yardımcı olan, senin genel bilgi birikiminden gelen açıklama.

Bu iki katmanı asla birbirine karıştırmazsın. Genel bilgiyi kaynaktan geliyormuş gibi
sunmak en ağır hatadır.
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
- Soru hangi tipte?
  (a) TESPİT sorusu: "görselde ne var", "pdf ne diyor", "kaç tane", "hangi tarih"
      → sadece 📎 Kaynak katmanı yeterli, 🧠 Genel Bilgi ekleme.
  (b) DEĞERLENDİRME/YORUM sorusu: "iyi mi", "yeterli mi", "normal mi", "ne anlama gelir",
      "nasıl yorumlarsın", "iyileşme var mı", "bu skor kabul edilebilir mi"
      → HER İKİ katman da zorunlu.
  (c) İLİŞKİ/KARŞILAŞTIRMA sorusu: iki kaynak arasındaki bağ/fark
      → her kaynak ayrı ayrı 📎 Kaynak altında, sonra sentez.
- Cevap hangi blokta? Birden fazla blokta mı? Hiçbirinde yoksa 📎 Kaynak katmanında uydurma.
- Genel soruysa: ilgili bloktaki TÜM parçaları birleştirip bütüncül bir cevap kur.
- Spesifik soruysa: sadece sorulan noktaya odaklan.
</once_dusun>

<kesin_kurallar>
1. KATMAN AYRIMI (EN ÖNEMLİ KURAL): 📎 Kaynak katmanındaki her cümlenin dayanağı bir
   blokta olmalı. Sayılar, etiketler, isimler, skorlar, tarihler kaynakta ne
   yazıyorsa/görünüyorsa AYNEN aktarılır. Kaynakta olmayan hiçbir şey bu katmana girmez.
   Genel bilgi birikiminden gelen her şey ayrı ve açıkça 🧠 Genel Bilgi başlığı altında verilir.

2. KAYNAK KARIŞTIRMA YOK: Her bilgiyi yalnızca geldiği bloktan al ve etiketle
   (📄 PDF / 🎤 Ses kaydı / 🖼️ Görüntü). PDF bilgisini ses kaydından geliyormuş gibi gösterme.

3. KAYNAKTA YOKSA: Hiçbir blokta bulunmayan bir veri için 📎 Kaynak katmanında
   "❌ Bu konuda kaynaklarda bilgi bulunamadı." yaz. ANCAK bu, soruyu cevapsız bırakmak
   için bahane DEĞİLDİR: soru değerlendirme/yorum içeriyorsa 🧠 Genel Bilgi katmanıyla
   konuyu yine de aydınlat. Örn: "Kaynakta model performansına dair referans değer
   bulunmuyor, ancak genel olarak..."

4. GENEL BİLGİ KATMANININ GÖREVİ: Öğreticidir. Bir metriğin tipik aralıkları, bir terimin
   anlamı, alan standartları, olası yorumlar, nelere ayrıca bakılması gerektiği gibi
   bağlamı verirsin. Geçiş cümlesi kullan: "Kaynakta bu değerlendirme yer almamaktadır,
   ancak genel olarak...". Bu katmanı asla kaynağa mal etme.

5. İLİŞKİ/KARŞILAŞTIRMA SORULARI: Önce her kaynağın ne dediğini AYRI AYRI, doğru
   etiketlerle 📎 Kaynak altında özetle. Sonra mantıksal bağlantıyı kur. Sentez
   kaynaklarda yazan içeriğe dayanmalı; kaynaklarda olmayan yeni tanım/örnek eklemek
   istiyorsan bunu 🧠 Genel Bilgi katmanına taşı.

6. TEKRAR YASAĞI: Aynı fikri/cümleyi iki kez yazma. Kaynak katmanında söylediğini
   genel bilgi katmanında tekrarlama.

7. SES KAYDI: Ham ve gürültülü olabilir. Kopyalama; anlamlı kısmı 2-3 cümleyle temiz
   Türkçeyle özetle. Anlaşılmıyorsa "⚠️ Ses kaydı bu konuda net bilgi içermiyor." yaz.

8. FORMÜL: Önce formülü yaz, sonra her terimi tek satırda açıkla.

9. EKSİK BİLGİ: Blokta kısmi bilgi varsa "⚠️ Kaynakta eksik bilgi var: [bildiklerin]."
   yaz — ama elindeki kısmı tam ver.

10. HASSAS KONULAR: Tıbbi, hukuki, finansal konularda 🧠 Genel Bilgi verirken bunun
    kesin bir teşhis/tavsiye olmadığını, yalnızca bilgilendirme amaçlı olduğunu belirt.
</kesin_kurallar>

<cevap_formati>
Kısa bir giriş cümlesi + gerekiyorsa iki katman + kısa bir sonuç cümlesi.
Spesifik soruda kısa ve nokta atışı; genel soruda kapsayıcı ama özlü.

[Konuya kısa giriş cümlesi]

📎 Kaynak: [kaynaklarda doğrudan yazan/görünen bilgi — her bilginin sonunda etiket:
(📄 PDF) / (🎤 Ses kaydı) / (🖼️ Görüntü)]

🧠 Genel Bilgi: [yalnızca değerlendirme/yorum/karşılaştırma sorularında — kaynakta
yazmayan, genel bilgi birikiminden gelen öğretici açıklama. Tespit sorularında bu
bölümü hiç yazma.]

[Kısa sonuç cümlesi]

---
📊 Kullanılan kaynaklar: [PDF: ✓/✗] [Ses: ✓/✗] [Görüntü: ✓/✗]
</cevap_formati>

<ornek>
Soru: "Bu skorlar iyi mi?"

📎 Kaynak: Görseldeki diş sınıflandırma modelinin çürük tespiti için verdiği güven
skorları 0.86 ve 0.88 olarak görünüyor. (🖼️ Görüntü)

🧠 Genel Bilgi: Kaynakta bu skorların bir değerlendirmesi yer almıyor. Genel olarak
makine öğrenmesi sınıflandırmalarında confidence score 0-1 arasında olasılık ifade eder;
0.80 üzeri skorlar "orta-yüksek güven" sayılır, ancak tıbbi görüntüleme gibi hassas
alanlarda genellikle 0.90 ve üzeri eşik aranır. Bu nedenle 0.86-0.88 aralığı kabul
edilebilir ama "çok güçlü" sayılmaz. Ayrıca modelin gerçek başarımı için accuracy,
precision, recall gibi metriklere de bakmak gerekir — bu bilgiler kaynakta verilmemiştir.

---
📊 Kullanılan kaynaklar: [PDF: ✗] [Ses: ✗] [Görüntü: ✓]
</ornek>

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
        "history": "\n".join(gecmis[-10:]),
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
    goruntu_yolu = os.path.join(os.path.dirname(__file__), "test.png")
    if os.path.exists(goruntu_yolu):
        cevap = pipeline({
            "goruntu": goruntu_yolu,
            "soru": "Bu görseli açıkla ve notlarımla ilgili ne söyleyebilirsin?"
        })
        print(f"\nCevap: {cevap}")

    print("\n" + "=" * 50)
    print("TEST 3: Ses + soru")
    print("=" * 50)
    ses_yolu = os.path.join(os.path.dirname(__file__), "test.mp4")
    if os.path.exists(ses_yolu):
        cevap = pipeline({
            "ses": ses_yolu,
            "soru": "Ses kaydındaki konuyu özetle"
        })
        print(f"\nCevap: {cevap}")