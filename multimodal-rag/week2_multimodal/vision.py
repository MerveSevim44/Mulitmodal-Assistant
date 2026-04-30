from groq import Groq
from dotenv import load_dotenv
import os
import base64

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def goruntu_analiz(dosya_yolu: str, soru: str = None) -> str:
    """Görüntüyü analiz eder"""
    if not os.path.exists(dosya_yolu):
        raise FileNotFoundError(f"Dosya bulunamadı: {dosya_yolu}")
    
    # Görüntüyü base64'e çevir
    with open(dosya_yolu, "rb") as f:
        goruntu_b64 = base64.b64encode(f.read()).decode("utf-8")
    
    uzanti = dosya_yolu.split(".")[-1].lower()
    mime_type = f"image/{uzanti}" if uzanti != "jpg" else "image/jpeg"
    
    if soru is None:
        soru = """Bu görseli çok dikkatli analiz et:
        - Görüntüde tam olarak ne var? (veri yapısı, diyagram, grafik, kod, formül, metin?)
        - Varsa düğümler, oklar, bağlantılar neler?
        - Varsa sayısal değerleri ve etiketleri yaz
        - Varsa başlık veya metin içeriğini yaz
        - Bu görüntü hangi konuyu anlatıyor? (linked list, binary tree, algoritma vb.)
        Yalnızca gördüklerini yaz, tahmin etme."""
    
    print(f"Görüntü analiz ediliyor: {dosya_yolu}")
    yanit = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{goruntu_b64}"
                    }
                },
                {
                    "type": "text",
                    "text": soru
                }
            ]
        }]
    )
    return yanit.choices[0].message.content

if __name__ == "__main__":
    test_goruntu = "week2_multimodal/data/test.png"
    
    if os.path.exists(test_goruntu):
        analiz = goruntu_analiz(test_goruntu)
        print(f"\nGenel Analiz:\n{analiz}")
        print("-" * 40)
        
        cevap = goruntu_analiz(test_goruntu, "Bu görseldeki en önemli bilgi nedir?")
        print(f"\nSpesifik Soru:\n{cevap}")
    else:
        print("Test görüntüsü bulunamadı!")
        print("week2_multimodal/data/ klasörüne test.png ekle")