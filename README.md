# 🎓 Akademik Bellek Asistanı (Academic Memory Assistant)

Multimodal RAG (Retrieval Augmented Generation) tabanlı, **Türkçe** akademik yardımcı sistemi. Ders PDF'lerinizi, ses kayıtlarınızı ve görsellerinizi tek bir bellekte toplar; doğal dille sorduğunuz sorulara **yalnızca kendi kaynaklarınıza dayanarak** cevap üretir.

> Streamlit arayüzü üzerinden dersleri ve konuları organize eder, her konu için ayrı sohbet geçmişi tutar ve cevapların hangi kaynaktan (📄 PDF / 🎤 Ses / 🖼️ Görüntü) geldiğini etiketler.

---

## 📋 İçindekiler

- [Proje Nedir?](#-proje-nedir)
- [Özellikler](#-özellikler)
- [Sistem Mimarisi](#️-sistem-mimarisi)
- [Teknoloji Stack'i](#teknoloji-stacki)
- [Gereksinimler](#-gereksinimler)
- [Kurulum](#-kurulum)
- [Kullanım](#-kullanım)
- [Proje Yapısı](#-proje-yapısı)
- [Çalışma Akışı (Teknik)](#️-çalışma-akışı-teknik)
- [Sorun Giderme](#-sorun-giderme)
- [SSS](#-sss)

---

## 🎯 Proje Nedir?

**Akademik Bellek Asistanı**, üniversite öğrencilerinin ve eğitmenlerin ders materyallerini akıllıca yönetip sorgulamasına yardımcı olan bir web uygulamasıdır.

### Ana Kullanım Senaryosu
1. Ders **PDF**'lerini, **ses kayıtlarını** veya **görselleri/diyagramları** sisteme yüklersiniz.
2. Materyalleri **ders → konu** hiyerarşisinde organize edersiniz.
3. Doğal dilde soru sorarsınız; sistem ilgili parçaları bulup bağlamsal cevap üretir.
4. İsterseniz aktif bir **görsel** veya **ses kaydını** o soruya dahil ederek çok kaynaklı (multimodal) cevap alırsınız.

Sistemin en önemli ilkesi **topraklama (grounding)**: model yalnızca yüklediğiniz kaynaklarda yazan bilgiyi kullanır, kaynakta olmayan şeyi uydurmaz ("❌ Bu konuda kaynaklarda bilgi bulunamadı.").

---

## ✨ Özellikler

### 📚 Organizasyon
- **Ders Yönetimi**: Ders oluştur, adını düzenle, sil.
- **Konu Yönetimi**: Her derse konular ekle; materyaller konu bazında indekslenir.
- **Kalıcı Depo**: Ders/konu yapısı `dersler.json`, sohbetler `sohbetler.json` içinde JSON olarak saklanır.
- **Konu Bazlı Sohbet**: Her ders–konu kombinasyonu kendi sohbet geçmişine ve kaynaklarına sahiptir; konular arası sızma olmaz.

### 📥 Çok Kaynaklı Yükleme (Ingest)
- **📄 PDF**: Sayfa sayfa metin çıkarma → parçalama → ChromaDB'ye indeksleme.
- **🎤 Ses**: `mp4 / mp3 / wav / m4a` dosyalarını **Groq Whisper** ile Türkçe metne çevirme.
- **🖼️ Görüntü**: `png / jpg / jpeg` görsellerini **OpenRouter Vision** ile sınıflandırıp detaylı analiz etme.
- **Yinelenen koruması**: Aynı dosya aynı konuya tekrar yüklenirse eski parçalar silinip yeniden indekslenir (duplikasyon olmaz).

### 💬 Akıllı Cevaplama
- **Kaynak yönlendirme**: Sorudaki anahtar kelimelere göre (örn. "derste hoca…" → ses, "diyagramda…" → görüntü) ilgili kaynağa öncelik verilir.
- **MMR retrieval**: Tekrar eden parçalar yerine çeşitlilik veren `max_marginal_relevance_search` ile tanım + örnek + uygulama bir arada yakalanır.
- **Etiketli yanıt**: Her bilgi geldiği kaynakla işaretlenir; ilişki/karşılaştırma sorularında ayrı bir sentez paragrafı üretilir.
- **Konuşma hafızası**: Son turlar bağlama eklenir; "peki ya bu?" gibi atıflar çözülür.

---

## 🏗️ Sistem Mimarisi

```
┌────────────────────────────────────────────────────────────┐
│                 STREAMLIT WEB ARAYÜZÜ (main.py)            │
│        Ders/Konu yönetimi · Yükleme · Sohbet paneli         │
└───────────────┬──────────────────────────┬─────────────────┘
                │                          │
     ┌──────────▼──────────┐    ┌──────────▼────────────────┐
     │  YÜKLEME (ingest)   │    │   SORGU (pipeline.py)     │
     │  ingest_rag.py      │    │                            │
     │  ├─ PDF  → metin    │    │  ├─ kaynak_belirle()       │
     │  ├─ Ses  → Whisper  │    │  ├─ PDF  bağlamı getir     │
     │  └─ Görüntü → Vision │    │  ├─ Ses  bağlamı getir     │
     └──────────┬──────────┘    │  ├─ Görüntü anlık analiz   │
                │               │  └─ Groq LLM → cevap        │
                ▼               └──────────┬────────────────┘
     ┌─────────────────────────────────────▼─────────────────┐
     │            ChromaDB (Lokal Vektör Veritabanı)          │
     │  Embedding: multilingual-MiniLM-L12 (384D)             │
     │  Metadata: ders_id, konu_id, kaynak, dosya, tarih      │
     └────────────────────────────────────────────────────────┘
```

### Teknoloji Stack'i

| Bileşen | Teknoloji | Rol |
|---|---|---|
| **Web Arayüzü** | Streamlit | Kullanıcı arayüzü (`main.py`) |
| **RAG Framework** | LangChain | Pipeline ve prompt yönetimi |
| **Vektör DB** | ChromaDB (`langchain-chroma`) | Belge depolama & benzerlik araması |
| **Embeddings** | HuggingFace `paraphrase-multilingual-MiniLM-L12-v2` | Metin → 384B vektör (çok dilli) |
| **LLM (Cevap)** | Groq — `openai/gpt-oss-120b` | Bağlamsal cevap üretme |
| **Ses → Metin (STT)** | Groq Whisper — `whisper-large-v3-turbo` | Türkçe transkripsiyon |
| **Görüntü Analizi** | OpenRouter — `meta-llama/llama-4-maverick` | Diyagram/görsel analizi (OpenAI SDK ile) |
| **Ses Ön İşleme** | pydub + ffmpeg | Mono/16kHz sıkıştırma |
| **Kalıcı Depo** | JSON (`depo.py`) | Ders/konu/sohbet verisi |

---

## 📦 Gereksinimler

### Sistem
- **Python 3.10+**
- **ffmpeg** (ses işleme için zorunlu — pydub buna bağlıdır)
- ~2GB disk alanı (embedding modeli + bağımlılıklar)
- İlk kurulumda internet bağlantısı

### API Anahtarları
| Anahtar | Ne için? | Nereden? |
|---|---|---|
| `GROQ_API_KEY` | LLM cevapları **ve** Whisper ses→metin | https://console.groq.com |
| `OPENROUTER_API_KEY` | Görüntü/diyagram analizi | https://openrouter.ai/keys |

> İkisi de ücretsiz katmanla başlar. Bu projede Google Gemini **kullanılmıyor**; görüntü analizi OpenRouter üzerinden yapılır.

---

## 🚀 Kurulum

### 1️⃣ Depoyu klonla
```bash
git clone <repository-url>
cd "Multimodal Assistant"
```

### 2️⃣ Sanal ortam oluştur
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Bağımlılıkları kur
```bash
pip install -r requirements.txt
```

GPU'n varsa PyTorch'u GPU destekli sürümle değiştirebilirsin:
```bash
# NVIDIA GPU (CUDA 12.1)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 4️⃣ ffmpeg kur
Ses dosyalarının işlenmesi için ffmpeg gerekir:
```bash
# Windows  → https://www.gyan.dev/ffmpeg/builds/ (indir, PATH'e ekle)
# macOS    → brew install ffmpeg
# Ubuntu   → sudo apt-get install ffmpeg
```

> ⚠️ **Not:** `multimodal-rag/week2_multimodal/stt.py` içinde ffmpeg yolu şu an sabit (`C:\Users\merve\Desktop\ffmpeg\bin\...`) olarak yazılıdır. Kendi makinende çalıştırırken bu yolu kendi ffmpeg konumuna göre güncelle veya ffmpeg'i PATH'e ekleyip bu satırları kaldır.

### 5️⃣ API anahtarlarını ayarla
Proje kökünde `.env` dosyası oluştur:
```bash
GROQ_API_KEY=your_groq_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

---

## 💻 Kullanım

### Web arayüzünü başlat
```bash
streamlit run main.py
```
Tarayıcı otomatik açılır → `http://localhost:8501`

### Temel iş akışı

**1. Ders oluştur** — Sol panel → *➕ Yeni Ders* → ad gir → *Oluştur*.

**2. Konu ekle** — Dersi aç → *➕ Yeni Konu Ekle* → konu adı → *Konu Oluştur*.

**3. Materyal yükle** — Konuyu aç, sol kolondan:
- **📄 PDF Ekle** → dosya seç → *PDF Ekle* (sayfa sayfa metin çıkarılır, indekslenir)
- **🎤 Ses Ekle** → `mp4/mp3/wav/m4a` → *Ses Ekle* (Whisper ile Türkçe metne çevrilir)
- **🖼️ Görüntü Ekle** → `png/jpg/jpeg` → *Görüntüyü Ekle* (Vision ile analiz edilir)

**4. Soru sor** — Sağ kolondaki sohbet kutusuna yaz. İstersen *🖼️ Görüntüyü dahil et* / *🎤 Ses kaydını dahil et* kutularını işaretleyerek aktif kaynağı o soruya kat.

---

## 📁 Proje Yapısı

```
Multimodal Assistant/
├── main.py                          # 🎯 Streamlit uygulaması (arayüz + akış)
├── requirements.txt                 # 📦 Bağımlılıklar
├── .env                             # 🔐 API anahtarları (.gitignore'da)
├── README.md                        # 📖 Bu dosya
│
└── multimodal-rag/
    ├── depo.py                      # 💾 Ders/konu JSON yönetimi (CRUD)
    ├── dersler.json                 # Ders/konu hiyerarşisi (kalıcı)
    ├── sohbetler.json               # Konu bazlı sohbet geçmişi
    ├── prompts/
    │   └── diyagram_turleri.yaml    # Görsel sınıflandırma türleri (vision prompt)
    │
    ├── week1_rag/                   # Hafta 1 — Temel RAG
    │   ├── ingest_rag.py            # PDF/Ses/Görüntü → ChromaDB yükleme
    │   ├── retriever.py             # MMR tabanlı belge getirme
    │   ├── rag_chain.py             # LangChain RAG zinciri
    │   ├── test_groq.py             # Groq bağlantı testi
    │   └── chroma_db/               # 🗄️ Vektör veritabanı (SQLite)
    │
    └── week2_multimodal/            # Hafta 2 — Multimodal
        ├── pipeline.py             # 🔄 Sorgu pipeline'ı (retrieval + LLM)
        ├── stt.py                  # Ses → Metin (Groq Whisper + pydub)
        ├── vision.py               # Görüntü analizi (OpenRouter Vision)
        └── data/                   # 📂 Yüklenen geçici dosyalar
```

---

## ⚙️ Çalışma Akışı (Teknik)

### Yükleme (ingest)
```
PDF      → pypdf ile sayfa metni → RecursiveCharacterTextSplitter (chunk=500/overlap=50)
Ses      → pydub (mono/16kHz) → Groq Whisper (whisper-large-v3-turbo, tr) → metin → chunk
Görüntü  → OpenRouter Vision: (1) tür sınıflandır (2) türe göre detaylı analiz → metin
                        ↓
         multilingual-MiniLM-L12 embedding → ChromaDB (+ metadata: ders_id, konu_id, kaynak, dosya, tarih)
```

### Sorgu (pipeline.py)
```
Soru → kaynak_belirle() (anahtar kelimeyle PDF/Ses/Görüntü yönlendirmesi)
     → konu_id filtresiyle PDF ve Ses bağlamlarını ayrı ayrı MMR ile getir
     → (varsa) aktif görüntüyü anlık analiz et
     → hepsini etiketli prompt'a yerleştir → Groq LLM → topraklanmış cevap
```

### Önemli parametreler
| Parametre | Değer | Dosya |
|---|---|---|
| Embedding modeli | `paraphrase-multilingual-MiniLM-L12-v2` | `retriever.py`, `ingest_rag.py` |
| Retrieval | MMR, `k=8`, `fetch_k=25` | `retriever.py` |
| Chunk boyutu | 500 karakter / 50 örtüşme | `ingest_rag.py` |
| LLM | `openai/gpt-oss-120b`, `temperature=0`, `max_tokens=1000` | `pipeline.py` |
| Whisper | `whisper-large-v3-turbo`, `language="tr"` | `stt.py` |
| Vision | `meta-llama/llama-4-maverick` | `vision.py` |

---

## 🐛 Sorun Giderme

| Sorun | Çözüm |
|---|---|
| `ModuleNotFoundError` | `pip install -r requirements.txt` çalıştır |
| ffmpeg / pydub hatası (`Couldn't find ffmpeg`) | ffmpeg'i kur ve `stt.py` içindeki sabit ffmpeg yolunu güncelle |
| Groq API hatası | `.env` içinde `GROQ_API_KEY` doğru mu kontrol et |
| Görüntü analizi başarısız | `.env` içinde `OPENROUTER_API_KEY` ekli mi kontrol et |
| `diyagram_turleri.yaml not found` | `multimodal-rag/prompts/` klasörünün yerinde olduğundan emin ol |
| ChromaDB bozuldu | `multimodal-rag/week1_rag/chroma_db/` klasörünü sil ve materyalleri yeniden yükle |
| Port kullanımda | `streamlit run main.py --server.port 8502` |

---

## ❓ SSS

**S: Cevaplar neden bazen "kaynaklarda bilgi bulunamadı" diyor?**
A: Sistem bilerek topraklanmıştır — yalnızca yüklediğin materyallerde yazan bilgiyi kullanır, uydurmaz. İlgili dosyayı doğru konuya yüklediğinden emin ol.

**S: Aynı PDF'i iki kez yüklersem ne olur?**
A: Eski parçalar otomatik silinip yeniden indekslenir; tekrar (duplikasyon) oluşmaz.

**S: Hangi diller destekleniyor?**
A: Arayüz ve cevaplar Türkçe odaklıdır; embedding modeli çok dilli, Whisper Türkçe'ye ayarlıdır.

**S: Google Gemini gerekli mi?**
A: Hayır. Görüntü analizi OpenRouter, ses ve LLM Groq üzerinden çalışır. `requirements.txt` içinde Gemini paketi bulunsa da kod onu kullanmaz.

**S: İnternetsiz çalışır mı?**
A: Hayır. LLM (Groq), STT (Groq) ve görüntü (OpenRouter) bulut API'leridir; sadece embedding ve ChromaDB lokaldir.

---

**Versiyon:** 2.0 (Multimodal RAG)
Sorularınız için GitHub Issues açabilirsiniz. 🚀
