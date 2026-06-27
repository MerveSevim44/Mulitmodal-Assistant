import ollama
import base64
import os

def goruntu_analiz(dosya_yolu: str, soru: str = None) -> str:
    if not os.path.exists(dosya_yolu):
        raise FileNotFoundError(f"Dosya bulunamadı: {dosya_yolu}")
    
    if soru is None:
        soru = """Bu görseli çok dikkatli analiz et:
        - Görüntüde tam olarak ne var? (veri yapısı, diyagram, grafik, kod, formül, metin?)
        - Varsa düğümler, oklar, bağlantılar neler?
        - Varsa sayısal değerleri ve etiketleri yaz
        - Varsa başlık veya metin içeriğini yaz
        - Bu görüntü hangi konuyu anlatıyor?
        Yalnızca gördüklerini yaz, tahmin etme."""

    with open(dosya_yolu, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    response = ollama.chat(
        model="llava",
        messages=[{
            "role": "user",
            "content": soru,
            "images": [b64]
        }]
    )
    return response["message"]["content"]