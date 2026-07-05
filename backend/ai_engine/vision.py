"""
Image analysis module using OpenRouter Vision API.
Migrated from week2_multimodal/vision.py — cleaned imports.
"""
import os
import base64
import yaml
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenRouter client
_client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

# Load diagram classification types from YAML
_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
_YAML_PATH = os.path.join(_PROMPTS_DIR, "diyagram_turleri.yaml")

_types = []
_type_names = ""
_type_details = ""

if os.path.exists(_YAML_PATH):
    with open(_YAML_PATH, "r", encoding="utf-8") as f:
        _types = yaml.safe_load(f).get("turler", [])
    _type_names = ", ".join(t["ad"] for t in _types)
    _type_details = "\n".join(f"  * {t['ad']}: {t['isaretler']}" for t in _types)


def analyze_image(
    file_path: str,
    model: str = None,
    question: str = None,
) -> str:
    """
    Analyze an image using a two-step process:
    1. Classify the diagram/image type
    2. Perform detailed analysis based on the type

    Args:
        file_path: Path to the image file (png, jpg, jpeg)
        model: Vision model to use (defaults to llama-4-maverick)
        question: Optional specific question about the image

    Returns:
        Formatted analysis string with type and details
    """
    if model is None:
        model = os.getenv("VISION_MODEL", "meta-llama/llama-4-maverick")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Image file not found: {file_path}")

    # Read and encode image
    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    ext = file_path.rsplit(".", 1)[-1].lower()
    mime = f"image/{ext}" if ext != "jpg" else "image/jpeg"

    # Step 1: Classify the image type
    classify_prompt = f"""Bu görselin TÜRÜNÜ belirle. Aşağıdaki türlerden HANGİSİNE en çok uyduğunu söyle:

    {_type_details}

    ÖNEMLİ AYIRT ETME KURALI:
    - Eğer kutular DURUMLARI gösteriyorsa (Reading X, Waiting, Processing gibi isimler) 
    ve oklar üzerinde TETİKLEYİCİ OLAY etiketleri varsa (X Pressed, X Successfully, 
    X Failed gibi) → bu DURUM GEÇİŞ DİYAGRAMI'dır, akış diyagramı DEĞİL.
    - Eğer kutular EYLEMLER/İŞLEMLER ise (Hesapla, Yazdır, Topla gibi fiil) ve oklar 
    üzerinde etiket YOKSA → bu AKIŞ DİYAGRAMI'dır.

    Sadece tür adını yaz (örnek: "Durum geçiş diyagramı"). Başka açıklama yapma."""

    classification = _vision_call(b64, mime, classify_prompt, model).strip()
    print(f"Image type classified: {classification}")

    # Step 2: Detailed analysis based on type
    detail_prompt = f"""Bu görsel bir "{classification}". Buna uygun şekilde analiz et:
- Tüm bileşenleri (düğüm, ok, kutu, etiket, değer) listele
- Ok ÜZERİNDEKİ etiketleri özellikle yaz (varsa)
- Bağlantıları/ilişkileri açıkla
- Varsa sayısal değerleri ve başlık/metin içeriğini yaz
- Hangi konuyu anlatıyor?
Yalnızca gördüklerini yaz, tahmin etme."""

    detail = _vision_call(b64, mime, detail_prompt, model)

    return f"GÖRSEL TÜRÜ: {classification}\n\nDETAYLI ANALİZ:\n{detail}"


def _vision_call(b64: str, mime: str, prompt: str, model: str) -> str:
    """Make a vision API call to OpenRouter."""
    response = _client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    return response.choices[0].message.content
