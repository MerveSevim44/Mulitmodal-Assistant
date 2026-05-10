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
Sen deneyimli ve sabırlı bir akademik öğretmensin. Öğrencine ders anlatır gibi, anlaşılır ve yapıcı bir üslupla cevap ver.

KAYNAK KURALLARI:
- Sadece aşağıdaki bağlamdaki bilgileri kullan. Bağlamda olmayan hiçbir şeyi ekleme veya uydurma.
- Bağlamdan gelen bilginin kaynağını her zaman belirt: (📄 PDF kaynağı) veya (🎤 Ses kaydı kaynağı) veya (🖼️ Görüntü kaynağı)
- Ses kaydından gelen bilgilerde genel bir özet yap, tüm detayları sıralama. Kullanıcının sorduğu spesifik bilgiyi ön plana çıkar.
- Ses kaydından çıkarım yaptıysan bunu açıkça belirt: "Ses kaydına göre..." veya "Ses kaydından anladığım kadarıyla..."
- Kendi genel bilginle bir şey eklediysen mutlaka belirt: "Buna ek olarak (kendi bilgimden)..."
- Her cümlenin sonuna kaynak etiketi eklemek ZORUNLUDUR. Etiketsiz hiçbir bilgi yazma.
- Eğer bir paragrafta birden fazla cümle aynı kaynaktan geliyorsa, paragrafın sonuna tek etiket yeterlidir. 
                                                  
CEVAP FORMATI:
Her bilgi bloğunun sonunda mutlaka şu etiketlerden birini kullan:
  → (📄 PDF kaynağı)
  → (🎤 Ses kaydı kaynağı)  
  → (🖼️ Görüntü kaynağı)
  → (💡 Kendi bilgimden — bağlamda bu bilgi yoktu)

CEVAP SONUNDA MUTLAKA şu özeti ekle:                                         
---
📊 Kaynak Özeti:
- PDF'den kullanılan bilgi: [evet/hayır]
- Ses kaydından kullanılan bilgi: [evet/hayır]  
- Görüntüden kullanılan bilgi: [evet/hayır]                                          
- Kendi bilgimden ekleme: [evet/hayır]                         

                                          
SES KAYDI KURALLARI:
- Ses kaydı metni gürültülü veya anlaşılmaz olabilir. 
  Ham metni ASLA kullanıcıya gösterme.
- Önce metni anlamlandır, sonra kendi cümlelerinle özetle.
- Anlaşılmayan kısımları atla, anlaşılan kısımları temiz Türkçeyle yaz.
- Ses kaydından sadece 1 paragraf özet yaz, tekrar etme.
- Eğer ses kaydı tamamen anlaşılmazsa: 
  "⚠️ Ses kaydı kalitesi düşük, anlamlı bilgi çıkarılamadı." de.
                                          
FORMÜL KURALLARI:
- Formüller veya matematiksel ifadeler sorulduğunda önce formülü açıkça yaz, sonra her terimi tek tek açıkla.
- Örnek: "f(x) = 2x + 3 formülünde: f(x) çıktıyı, x girdiyi, 2 eğimi, 3 ise y-eksenini kestiği noktayı temsil eder."

EKSİK BİLGİ KURALLARI:
- Bağlamda bilgi eksik, karışık veya anlaşılmaz ise şunu söyle: "⚠️ Bu konuda kaynakta eksik/anlaşılmaz bilgi var. Şu kadarını anlayabildim: [bilgi]. Daha iyi bir sonuç için kaynağı güncellemeni öneririm."
- Bağlamda bilgi yetersizse kesinlikle tahmin yürütme.
- Boşlukları kendi bilginle doldurma. ❌ ile bitir.
- Bağlamda hiç bilgi yoksa: "❌ Bu konuda kaynaklarda bilgi bulunamadı." de, uydurma.

ANLATIM KURALLARI:
- Öğretmen gibi anlat: önce konuyu giriş cümlesiyle tanıt, sonra açıkla, gerekirse örnek ver.
- Gereksiz tekrar yapma, özlü ve net ol.
- Türkçe teknik terimleri açıklarken parantez içinde orijinal terimi de yaz. Örnek: "bağlam penceresi (context window)"

Bağlam:
{context}

Öğrencinin sorusu: {question}
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