from openai import OpenAI
from dotenv import load_dotenv
import base64
import os
import yaml

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# YAML'dan diyagram türlerini yükle
# vision.py -> week2_multimodal -> multimodal-rag (prompts klasörü burada)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YAML_PATH = os.path.join(PROJECT_ROOT, "prompts", "diyagram_turleri.yaml")

with open(YAML_PATH, "r", encoding="utf-8") as f:
    _turler = yaml.safe_load(f)["turler"]

# Sınıflandırma için: sadece türlerin adlarını listele
_tur_adlari = ", ".join(t["ad"] for t in _turler)

# Detaylı analiz için: ad + işaretler birlikte
_tur_detaylari = "\n".join(f"  * {t['ad']}: {t['isaretler']}" for t in _turler)


def goruntu_analiz(dosya_yolu: str, soru: str = None) -> str:
    if not os.path.exists(dosya_yolu):
        raise FileNotFoundError(f"Dosya bulunamadı: {dosya_yolu}")

    with open(dosya_yolu, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    uzanti = dosya_yolu.split(".")[-1].lower()
    mime = f"image/{uzanti}" if uzanti != "jpg" else "image/jpeg"

    sinif_prompt = f"""Bu görselin TÜRÜNÜ belirle. Aşağıdaki türlerden HANGİSİNE en çok uyduğunu söyle:

    {_tur_detaylari}

    ÖNEMLİ AYIRT ETME KURALI:
    - Eğer kutular DURUMLARI gösteriyorsa (Reading X, Waiting, Processing gibi isimler) 
    ve oklar üzerinde TETİKLEYİCİ OLAY etiketleri varsa (X Pressed, X Successfully, 
    X Failed gibi) → bu DURUM GEÇİŞ DİYAGRAMI'dır, akış diyagramı DEĞİL.
    - Eğer kutular EYLEMLER/İŞLEMLER ise (Hesapla, Yazdır, Topla gibi fiil) ve oklar 
    üzerinde etiket YOKSA → bu AKIŞ DİYAGRAMI'dır.

    Sadece tür adını yaz (örnek: "Durum geçiş diyagramı"). Başka açıklama yapma."""

    sinif = _vision_call(b64, mime, sinif_prompt).strip()
    print(f"Görsel türü: {sinif}")

    # Adım 2: TÜRE GÖRE DETAYLI ANALİZ
    detay_prompt = f"""Bu görsel bir "{sinif}". Buna uygun şekilde analiz et:
- Tüm bileşenleri (düğüm, ok, kutu, etiket, değer) listele
- Ok ÜZERİNDEKİ etiketleri özellikle yaz (varsa)
- Bağlantıları/ilişkileri açıkla
- Varsa sayısal değerleri ve başlık/metin içeriğini yaz
- Hangi konuyu anlatıyor?
Yalnızca gördüklerini yaz, tahmin etme."""

    detay = _vision_call(b64, mime, detay_prompt)

    return f"GÖRSEL TÜRÜ: {sinif}\n\nDETAYLI ANALİZ:\n{detay}"


def _vision_call(b64: str, mime: str, prompt: str) -> str:
    response = client.chat.completions.create(
        model="meta-llama/llama-4-maverick",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                {"type": "text", "text": prompt}
            ]
        }]
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    test_goruntu = "C:\\Users\\merve\\Desktop\\miuul_generative_ai\\Multimodal Assistant\\multimodal-rag\\week2_multimodal\\data\\görsel_2026-06-28_182857124.png"
    
    if os.path.exists(test_goruntu):
        sonuc = goruntu_analiz(test_goruntu)
        print(f"\n{sonuc}")
    else:
        print("Test görüntüsü bulunamadı!")