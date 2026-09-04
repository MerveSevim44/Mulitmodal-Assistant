"""
AI Pipeline — core question-answering engine with streaming support.
Migrated from week2_multimodal/pipeline.py — async, streaming, no Streamlit deps.
"""
import os
import json
from typing import AsyncGenerator, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessageChunk
from dotenv import load_dotenv

from ai_engine.retriever import retrieve_text, get_vector_db
from ai_engine.vision import analyze_image

load_dotenv()

# ── LLM & PROMPT ────────────────────────────────────────────────

llm = ChatGroq(
    model=os.getenv("LLM_MODEL", "openai/gpt-oss-120b"),
    temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
    max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1000")),
)

prompt_template = ChatPromptTemplate.from_template(r"""
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
- Soru bir İLİŞKİ/KARŞILAŞTIRMA sorusu mu? ("X ile Y'nin ilişkisi nedir", "bu görsel pdf ile nasıl bağlantılı", "X ve Y arasındaki fark") → sentez kuralı devreye girer.
- Cevap hangi blokta? Birden fazla blokta mı? Hiçbirinde yoksa uydurma.
- Genel soruysa: ilgili bloktaki TÜM parçaları birleştirip bütüncül bir cevap kur, tek bir cümleye yapışma.
- Spesifik soruysa: sadece sorulan noktaya odaklan, fazlasını ekleme.
</once_dusun>

<kesin_kurallar>
1. TOPRAKLAMA: Her cümlenin dayanağı bir blokta olmalı. Blokta yoksa yazma. Genel kültüründen, tahminden ya da "muhtemelen"den asla bilgi ekleme.

2. KAYNAK KARIŞTIRMA YOK: Her bilgiyi yalnızca geldiği bloktan al ve etiketle. PDF bilgisini ses kaydından geliyormuş gibi gösterme.

3. UYDURMA YASAĞI: Hiçbir blokta olmayan bilgi için "❌ Bu konuda kaynaklarda bilgi bulunamadı." yaz ve dur. Bilgi yoksa boşluğu doldurma.

4. İLİŞKİ/KARŞILAŞTIRMA SORULARI (SENTEZ İSTİSNASI): Kullanıcı iki kaynak arasındaki ilişkiyi, bağlantıyı veya farkı sorduğunda farklı davran:
   - Önce her kaynağın ne dediğini AYRI AYRI özetle, doğru etiketlerle (📄 PDF / 🎤 Ses / 🖼️ Görüntü).
   - Sonra mantıksal bir karşılaştırma/bağlantı kur. Bu sentez senin yorumun.
   - Sentez kısmını kaynakta yazıyormuş gibi sunma. "Kaynaklardan çıkardığım kadarıyla...", "Bu ikisi şu açıdan benzer/farklıdır...", "PDF'teki kavram görseldeki örnekle şu şekilde örtüşür..." gibi açık dille ifade et.
   - Sentezde uydurma serbest DEĞİL: kıyaslama, kaynaklarda yazan içeriğe dayanmalı. Kaynaklarda olmayan yeni bilgi (yeni tanım, yeni örnek) ekleme.
   - Kaynaklardan biri (ör. ses) o soru için boşsa, sadece dolu olanlar üzerinden sentez yap.

5. TEKRAR YASAĞI: Aynı fikri/cümleyi iki kez yazma.

6. SES KAYDI: Ham ve gürültülü olabilir. Kopyalama; anlamlı kısmı 2-3 cümleyle temiz Türkçeyle özetle. Anlaşılmıyorsa "⚠️ Ses kaydı bu konuda net bilgi içermiyor." yaz.

7. FORMÜL (LaTeX ZORUNLU): Matematiksel her ifadeyi LaTeX ile yaz. Düz metin/Unicode matematik yazma.
   - Blok (kendi satırında duran) formül: boş satırla ayrılmış `$$ ... $$` kullan.
   - Satır içi formül/sembol: `$ ... $` kullan. Örn: $a_0$, $\omega_0$, $c_k=\sqrt{{a_k^2+b_k^2}}$.
   - ASLA `\[ ... \]`, `\( ... \)` veya çıplak `[ ... ]` sınırlayıcısı kullanma; yalnızca `$` ve `$$`.
   - Ters bölüleri kırpma: \int, \sum, \frac, \sqrt, \cos, \sin, \tan, \infty, \, aynen yazılır.
   - Alt/üst simgeler süslü parantezli: `a_{{k}}`, `\omega_{{0}}`, `k^{{2}}`.
   - Kaynak etiketini (📄 PDF vb.) formülün DIŞINA, sonraki satıra koy — `$$` bloğunun içine yazma.
   - Formülden sonra her terimi tek satırda, satır içi LaTeX ile açıkla.
   Örnek:
   $$x(t)=a_{{0}}+\sum_{{k=1}}^{{\infty}}\left[a_{{k}}\cos(k\omega_{{0}}t)+b_{{k}}\sin(k\omega_{{0}}t)\right]$$
   Burada $a_0$ ortalama bileşen, $\omega_0$ temel açısal frekanstır. → (📄 PDF)

8. EKSİK BİLGİ: Blokta kısmi bilgi varsa "⚠️ Kaynakta eksik bilgi var: [bildiklerin]. Kaynağı güncellemeni öneririm." yaz — ama elindeki kısmı tam ver.
</kesin_kurallar>

<cevap_formati>
Orta uzunluk. Spesifik soruda kısa ve nokta atışı; genel soruda kapsayıcı ama özlü; ilişki sorusunda her kaynak ayrı + sentez paragrafı.

[Konuya kısa giriş]

[Açıklama — her bilgi bloğunun sonuna etiket: → (📄 PDF) / (🎤 Ses kaydı) / (🖼️ Görüntü)]

[İlişki sorusuysa: "Kaynaklardan çıkardığım kadarıyla..." ile başlayan kısa sentez paragrafı]

---
📊 Kullanılan kaynaklar: [PDF: ✓/✗] [Ses: ✓/✗] [Görüntü: ✓/✗]
</cevap_formati>

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

    # Build context from each source
    image_context = "Bu sorgu için görüntü analizi yapılmadı."
    audio_context = "Bu konuda ses kaydında bilgi bulunamadı."
    pdf_context = "Bu konuda PDF kaynağında bilgi bulunamadı."

    if image_path:
        print("Analyzing image for query context...")
        image_context = analyze_image(image_path)

    # Retrieve PDF and audio chunks separately
    pdf_docs = retrieve_text(
        question, course_id=course_id, topic_id=topic_id, source_type="pdf_dokuman"
    )
    audio_docs = retrieve_text(
        question, course_id=course_id, topic_id=topic_id, source_type="ses_kaydi"
    )

    if pdf_docs:
        pdf_context = pdf_docs
    if audio_docs:
        audio_context = audio_docs

    chain = prompt_template | llm
    result = chain.invoke({
        "history": "\n".join(history[-10:]),
        "pdf_baglam": pdf_context,
        "ses_baglam": audio_context,
        "goruntu_baglam": image_context,
        "question": question,
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

    Yields:
        Individual text tokens
    """
    history = history or []

    # Build context (same as sync pipeline)
    image_context = "Bu sorgu için görüntü analizi yapılmadı."
    audio_context = "Bu konuda ses kaydında bilgi bulunamadı."
    pdf_context = "Bu konuda PDF kaynağında bilgi bulunamadı."

    if image_path:
        image_context = analyze_image(image_path)

    pdf_docs = retrieve_text(
        question, course_id=course_id, topic_id=topic_id, source_type="pdf_dokuman"
    )
    audio_docs = retrieve_text(
        question, course_id=course_id, topic_id=topic_id, source_type="ses_kaydi"
    )

    if pdf_docs:
        pdf_context = pdf_docs
    if audio_docs:
        audio_context = audio_docs

    # Build the chain input
    chain_input = {
        "history": "\n".join(history[-10:]),
        "pdf_baglam": pdf_context,
        "ses_baglam": audio_context,
        "goruntu_baglam": image_context,
        "question": question,
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
