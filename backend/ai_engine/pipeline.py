"""
AI Pipeline — core question-answering engine with streaming support.
Migrated from week2_multimodal/pipeline.py — async, streaming, no Streamlit deps.
"""
import asyncio
import os
import json
from typing import AsyncGenerator, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessageChunk
from dotenv import load_dotenv

from ai_engine.retriever import retrieve_text, retrieve_documents, get_vector_db
from ai_engine.vision import analyze_image

load_dotenv()

# ── LLM & PROMPT ────────────────────────────────────────────────

llm = ChatGroq(
    model=os.getenv("LLM_MODEL", "openai/gpt-oss-120b"),
    temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
    max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1000")),
)

prompt_template = ChatPromptTemplate.from_template("""
<rol>
Sen bir belge/görsel/ses analiz asistanısın. Öğrencinin sağladığı PDF, görüntü ve ses
kaynaklarını analiz eder, sorularını yanıtlarsın.
</rol>

<konusma_gecmisi>
{history}
</konusma_gecmisi>

<kaynak_bloklari>
[PDF]: {pdf_baglam}
[SES]: {ses_baglam}
[GÖRÜNTÜ]: {goruntu_baglam}
</kaynak_bloklari>

<soru_tipi_belirle>
Önce sorunun tipini belirle (bunu cevaba yazma, sadece karar ver):
- TESPIT: "ne var", "kaç tane", "hangi tarih" → sadece ne gördüğünü/okuduğunu aktar.
- DEGERLENDIRME: "iyi mi", "yeterli mi", "iyileşme var mı", "ne anlama gelir" →
  kaynak bilgisini ver + MUTLAKA genel bilgiyle yorumla.
- KARSILASTIRMA: iki kaynak arasında bağ/fark → her kaynağı ayrı özetle, sonra bağla.
</soru_tipi_belirle>

<altin_kural>
Cevabın HER ZAMAN iki parçası olabilir, birbirine KARIŞTIRMA:

📎 Kaynak → kaynaklarda YAZAN/GÖRÜNEN şey, aynen aktarılır, etiketlenir
           (📄 PDF / 🎤 Ses kaydı / 🖼️ Görüntü). Kaynakta yoksa:
           "❌ Bu konuda kaynaklarda bilgi bulunamadı" ya da kısmen varsa
           "⚠️ Kaynakta eksik bilgi var: [bildiğin kısım]" yaz.

🧠 Genel Bilgi → kaynakta OLMAYAN ama konuyu açıklayan, senin bilgi
                birikiminden gelen yorum/açıklama.

KRİTİK KURAL: Soru DEGERLENDIRME veya KARSILASTIRMA tipindeyse, 📎 Kaynak
bölümünde "❌" veya "⚠️" yazmış olman 🧠 Genel Bilgi bölümünü yazmanı
ENGELLEMEZ. İkisi HER ZAMAN BİRLİKTE yer alır. Sadece TESPIT sorularında
🧠 Genel Bilgi bölümünü hiç açma.
</altin_kural>

<format>
[kısa giriş]

📎 Kaynak: [...]

🧠 Genel Bilgi: [sadece DEGERLENDIRME/KARSILASTIRMA sorularında yazılır]

[kısa sonuç]

---
📊 Kullanılan kaynaklar: [PDF: ✓/✗] [Ses: ✓/✗] [Görüntü: ✓/✗]
</format>

<ornekler>
Soru: "Görselde ne var?" (TESPIT)
→ Sadece 📎 Kaynak yazılır, 🧠 Genel Bilgi YOKTUR.

Soru: "0.86, 0.88 bu skor iyi mi, iyileşme var mı?" (DEGERLENDIRME)
→
📎 Kaynak: Görseldeki modelin çürük tespitinde ürettiği güven skorları 0.86 ve
0.88 olarak görünüyor. (🖼️ Görüntü)
⚠️ Kaynakta eksik bilgi var: Bu skorların "iyi" sayılıp sayılmadığına dair eşik
değer ya da zaman içindeki değişim bilgisi kaynakta yok.
🧠 Genel Bilgi: Confidence score 0-1 arasında olasılık ifade eder; 0.80 üzeri
skorlar genelde "orta-yüksek güven" sayılır, tıbbi görüntülemede ise 0.90+ eşiği
aranır. Bu açıdan 0.86-0.88 kabul edilebilir ama güçlü sayılmaz. "İyileşme"
sorusuna cevap için aynı modelin farklı zamanlardaki skorlarının kıyaslanması
gerekir; tek anlık skor buna yetmez.
---
📊 Kullanılan kaynaklar: [PDF: ✗] [Ses: ✗] [Görüntü: ✓]

NOT: İkinci örnekte ⚠️ VE 🧠 Genel Bilgi AYNI CEVAPTA birlikte var. Bu ikisi
birbirini engellemez, bunu unutma.
</ornekler>

<diger_kurallar>
- Kaynak karıştırma: PDF bilgisini Ses'ten geliyormuş gibi gösterme.
- Ses kaydı gürültülüyse 2-3 cümleyle temiz özetle, anlaşılmıyorsa
  "⚠️ Ses kaydı bu konuda net bilgi içermiyor." yaz.
- Formül varsa önce formülü yaz, sonra terimleri tek satırda açıkla.
- Tıbbi/hukuki/finansal konularda 🧠 Genel Bilgi'nin kesin tavsiye olmadığını belirt.
- Aynı cümleyi iki katmanda tekrar etme.
</diger_kurallar>

<soru>
{question}
</soru>
""")


# ── SOURCE DETECTION ────────────────────────────────────────────

def detect_source(question: str) -> Optional[str]:
    """Detect which source type a question is targeting based on keywords."""
    q = question.lower()

    if any(k in q for k in ["ses", "kayıt", "derste", "hoca", "anlattı", "söyledi"]):
        return "ses_kaydi"
    elif any(k in q for k in ["pdf", "belgede", "dokümanda", "notlarda", "kitapta"]):
        return "pdf_dokuman"
    elif any(k in q for k in ["görüntü", "resim", "görselde", "fotoğraf", "şekil"]):
        return "goruntu"
    return None


# ── CONTEXT BUILDING ────────────────────────────────────────────

def build_contexts(
    question: str,
    course_id: str = None,
    topic_id: str = None,
    image_path: str = None,
) -> tuple[dict, list]:
    """
    Build the three source context blocks for the prompt.

    Every source type is retrieved from the vector store independently so the
    answer can label where each claim came from. An image attached to the
    current message is analyzed live and placed ahead of the stored image
    analyses for this topic.

    Returns:
        (contexts, image_files) where contexts has the keys 'pdf_baglam',
        'ses_baglam' and 'goruntu_baglam', and image_files lists the stored
        file names of the images whose analyses were used — so the caller can
        show the reader the actual image the answer is describing.
    """
    pdf_docs = retrieve_text(
        question, course_id=course_id, topic_id=topic_id, source_type="pdf_dokuman"
    )
    audio_docs = retrieve_text(
        question, course_id=course_id, topic_id=topic_id, source_type="ses_kaydi"
    )
    image_results = retrieve_documents(
        question, course_id=course_id, topic_id=topic_id, source_type="goruntu", k=3
    )

    image_parts = []
    if image_path:
        print("Analyzing image for query context...")
        image_parts.append(analyze_image(image_path))

    image_files = []
    for doc in image_results:
        image_parts.append(doc.page_content)
        file_name = (doc.metadata or {}).get("dosya")
        if file_name and file_name not in image_files:
            image_files.append(file_name)

    contexts = {
        "pdf_baglam": pdf_docs or "Bu konuda PDF kaynağında bilgi bulunamadı.",
        "ses_baglam": audio_docs or "Bu konuda ses kaydında bilgi bulunamadı.",
        "goruntu_baglam": "\n\n".join(image_parts)
        or "Bu konuda görüntü kaynağında bilgi bulunamadı.",
    }
    return contexts, image_files


# ── SYNCHRONOUS PIPELINE ────────────────────────────────────────

def run_pipeline(
    question: str,
    course_id: str = None,
    topic_id: str = None,
    image_path: str = None,
    audio_path: str = None,
    history: list = None,
) -> str:
    """
    Run the full RAG pipeline synchronously.

    Args:
        question: User's question
        course_id: Course ID for filtering
        topic_id: Topic ID for filtering
        image_path: Path to active image (if included)
        audio_path: Path to active audio (if included)
        history: Previous conversation turns

    Returns:
        Generated answer string
    """
    history = history or []

    contexts, _image_files = build_contexts(
        question, course_id=course_id, topic_id=topic_id, image_path=image_path
    )

    chain = prompt_template | llm
    result = chain.invoke({
        "history": "\n".join(history[-10:]),
        "question": question,
        **contexts,
    })

    # Update conversation history
    history.append(f"Öğrenci: {question}")
    history.append(f"Asistan: {result.content}")

    return result.content


# ── STREAMING PIPELINE ──────────────────────────────────────────

async def stream_pipeline(
    question: str,
    course_id: str = None,
    topic_id: str = None,
    image_path: str = None,
    audio_path: str = None,
    history: list = None,
    image_files_out: list = None,
) -> AsyncGenerator[str, None]:
    """
    Run the RAG pipeline with streaming token output.

    Yields individual tokens as they are generated by the LLM.

    Args:
        question: User's question
        course_id: Course ID for filtering
        topic_id: Topic ID for filtering
        image_path: Path to active image (if included)
        audio_path: Path to active audio (if included)
        history: Previous conversation turns
        image_files_out: If given, the stored file names of the images used as
            context are appended to it before the first token is yielded. A
            generator can only yield tokens, so this is how the caller learns
            which images to show alongside the answer.

    Yields:
        Individual text tokens
    """
    history = history or []

    # Retrieval embeds the question, queries Chroma and may run vision/STT —
    # all synchronous and slow. Off the event loop it goes, so a chat request
    # in flight does not stall every other request the server is serving.
    contexts, image_files = await asyncio.to_thread(
        build_contexts,
        question,
        course_id=course_id,
        topic_id=topic_id,
        image_path=image_path,
    )
    if image_files_out is not None:
        image_files_out.extend(image_files)

    # Build the chain input
    chain_input = {
        "history": "\n".join(history[-10:]),
        "question": question,
        **contexts,
    }

    # Stream tokens using LangChain's async streaming
    chain = prompt_template | llm
    full_response = ""

    async for chunk in chain.astream(chain_input):
        if hasattr(chunk, "content") and chunk.content:
            full_response += chunk.content
            yield chunk.content

    # Update history after streaming completes
    history.append(f"Öğrenci: {question}")
    history.append(f"Asistan: {full_response}")
