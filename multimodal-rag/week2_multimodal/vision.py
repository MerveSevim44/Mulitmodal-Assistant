from openai import OpenAI
import base64, os

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

def goruntu_analiz(dosya_yolu: str, soru: str = None) -> str:
    if not os.path.exists(dosya_yolu):
        raise FileNotFoundError(f"Dosya bulunamadı: {dosya_yolu}")

    if soru is None:
        soru = """Bu görseli çok dikkatli analiz et:
        - Görüntüde tam olarak ne var? (veri yapısı, diyagram, grafik, kod, formül, metin?)
        - Varsa düğümler, oklar, bağlantılar neler?
        - Varsa sayısal değerleri ve etiketleri yaz
        - Bu görüntü hangi konuyu anlatıyor?
        Yalnızca gördüklerini yaz, tahmin etme."""

    with open(dosya_yolu, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    uzanti = dosya_yolu.split(".")[-1].lower()
    mime = f"image/{uzanti}" if uzanti != "jpg" else "image/jpeg"

    response = client.chat.completions.create(
        model="meta-llama/llama-4-maverick",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                {"type": "text", "text": soru}
            ]
        }]
    )
    return response.choices[0].message.content