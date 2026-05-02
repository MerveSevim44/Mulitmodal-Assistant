# 🎓 Akademik Bellek Asistanı (Academic Memory Assistant)

Multimodal RAG (Retrieval Augmented Generation) tabanlı, **Türkçe** destekli akademik yardımcı sistemi. Metin, ses ve görselleri analiz ederek ders notlarınızdan akıllı cevaplar çıkarır.

---

## 📋 İçindekiler

- [Proje Nedir?](#proje-nedir)
- [Özellikler](#özellikler)
- [Sistem Mimarisi](#sistem-mimarisi)
- [Gereksinimler](#gereksinimler)
- [Kurulum](#kurulum)
- [Kullanım](#kullanım)
- [Proje Yapısı](#proje-yapısı)
- [Geliştirilecek Özellikler](#geliştirilecek-özellikler)

---

## 🎯 Proje Nedir?

**Akademik Bellek Asistanı**, üniversite öğrencileri ve eğitmenlerin ders notlarını akıllı bir şekilde yönetmesine ve sorgulamasına yardımcı olan bir web uygulamasıdır.

### Ana Kullanım Senaryosu:
1. Ders PDF'lerini, ses kayıtlarını veya ders notlarını sisteme yüklersiniz
2. Sistemi ders ve konulara göre organize edersiniz
3. Doğal dil ile sorular sorar ve bağlamsal cevaplar alırsınız
4. Görsel (resim, diyagram) ile sorular sorabileceğiniz gibi, ses kaydıyla da soru sorabilirsiniz

---

## ✨ Özellikler

### ✅ Hafta 1 - Temel RAG Sistemi
- 📄 **PDF Desteği**: Ders PDF'lerinden metin çıkarma ve indeksleme
- 🎙️ **Ses Desteği**: MP3, WAV dosyalarını metne dönüştürme (Whisper modeli)
- 🔍 **Benzerlik Araması**: ChromaDB üzerinde vektör tabanlı arama
- 🧠 **Akıllı Cevaplar**: Groq LLM kullanarak bağlamsal cevaplar üretme

### ✅ Hafta 2 - Multimodal Genişleme
- 👁️ **Görüntü Analizi**: Ders notlarında bulunan diyagramları ve görselleri analiz etme
- 🎤 **Gerçek Zamanlı Ses**: Mikrofon ile doğrudan soru sorma
- 📊 **Çoklu Kaynak Kullanımı**: Metin + Ses + Görüntü kombinasyonu ile cevaplar

### ✅ Organizasyon Özellikleri
- 📚 **Ders Yönetimi**: Dersleri oluştur, düzenle, sil
- 📌 **Konu Yönetimi**: Her derse konular ekle (Mikro kontrol)
- 💾 **Kalıcı Depo**: JSON tabanlı yerel veri depolama
- 🎨 **Modern UI**: Streamlit ile duyarlı, koyu tema arayüz

---

## 🏗️ Sistem Mimarisi

```
┌─────────────────────────────────────────────────────────┐
│              STREAMLIT WEB ARAYÜZÜ (main.py)           │
├─────────────────────────────────────────────────────────┤
│                                                         │
├─ RAG Pipeline (Week 1)          ├─ Multimodal Pipeline (Week 2)
│  ├─ PDF/Ses → Metin               │  ├─ Görüntü Analiz (Gemini)
│  ├─ Embedding (HuggingFace)       │  ├─ Ses → Metin (Whisper)
│  ├─ ChromaDB (Vektör DB)          │  └─ Kombinasyon
│  └─ Groq LLM (Cevap üretme)       │
│                                    │
├────────────────────────────────────┤
│                                    │
│    ChromaDB (Lokal Vektör DB)     │
│    - Ders notları vektörleri      │
│    - Metadata (ders, konu, kaynak)│
│                                    │
└─────────────────────────────────────────────────────────┘
```

### Teknoloji Stack'i

| Bileşen | Teknoloji | Rol |
|---------|-----------|-----|
| **Web Framework** | Streamlit | Kullanıcı arayüzü |
| **RAG Framework** | LangChain | Pipeline orchestration |
| **Vector DB** | ChromaDB | Belge depolama & arama |
| **Embeddings** | HuggingFace (all-MiniLM) | Metin → Vektör |
| **LLM** | Groq (Llama 3.3-70B) | Cevap üretme |
| **Ses Processing** | Whisper (transformers) | STT (Speech-to-Text) |
| **Görüntü Analiz** | Google Gemini Flash | Vision tasks |
| **Local LLM** | Ollama | Optional: Lokal modeller |

---

## 📦 Gereksinimler

### Sistem Gereksinimleri
- Python 3.10+
- Git
- ~2GB disk alanı (modeller için)
- İnternet bağlantısı (ilk kurulum için)

### API Keys Gerekli
1. **Groq API Key** (Ücretsiz)
   - https://console.groq.com
   - Kaydol → API Keys → Token oluştur

2. **Google Gemini API Key** (Ücretsiz)
   - https://ai.google.dev/gemini-api
   - API'yi etkinleştir → Kimlik bilgileri oluştur

### Opsiyonel
- **Ollama**: Lokal LLM çalıştırmak için (https://ollama.com)
- **CUDA/GPU**: Ses ve görüntü işlemesini hızlandırmak için

---

## 🚀 Kurulum

### 1️⃣ Depoyu Klonla
```bash
git clone <repository-url>
cd "Multimodal Assistant"
```

### 2️⃣ Sanal Ortam Oluştur (Recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Bağımlılıkları Kur
```bash
pip install -r requirements.txt
```

**Not:** Eğer GPU'nuz varsa PyTorch'u GPU destekli versiyonla değiştirin:
```bash
# NVIDIA GPU (CUDA 12.1)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121

# Apple Silicon
pip install torch torchvision torchaudio
```

### 4️⃣ API Keys Yapılandır
`.env` dosyası oluştur (proje kökünde):
```bash
# Groq API Key (https://console.groq.com)
GROQ_API_KEY=your_groq_api_key_here

# Google Gemini API Key (https://ai.google.dev/gemini-api)
GOOGLE_API_KEY=your_google_api_key_here

# (Opsiyonel) Ollama lokal URL
OLLAMA_API_BASE=http://localhost:11434
```

### 5️⃣ (Opsiyonel) Ollama Kur
```bash
# Ollama indir ve kur: https://ollama.com

# Modelleri indir (terminal ayrı penceresinde)
ollama pull llama3.2
ollama pull llava        # Görüntü analizi için
ollama pull mistral      # Alternatif LLM
```

---

## 💻 Kullanım

### 🌐 Web Arayüzü Başlat
```bash
streamlit run main.py
```

Tarayıcınız otomatik açılacak → `http://localhost:8501`

### 📚 Temel İş Akışı

#### **Adım 1: Ders Oluştur**
1. **Sidebar → "Yeni Ders Ekle"** bölümüne git
2. Ders adı gir (örn: "İşletim Sistemleri", "Veri Tabanları")
3. **"Ekle"** butonuna tıkla

#### **Adım 2: Konular Ekle**
1. Oluşturduğun dersi seç
2. **Konu Ekle** bölümüne konu adı gir (örn: "Thread Yönetimi", "SQL Sorguları")
3. **Ekle** butonuna tıkla

#### **Adım 3: Belge Yükle**
Şu tipte dosyalar yükleyebilirsin:

**📄 PDF Yükleme:**
- "PDF Dosyası Yükle" → PDF seç
- İçerik otomatik çıkarılır ve ChromaDB'ye eklenir

**🎙️ Ses Yükleme:**
- "Ses Dosyası Yükle" (MP3, WAV, M4A)
- Whisper modeli ses → metin dönüştürür
- MetaData olarak kaydedilir

**🖼️ Görüntü Yükleme:**
- "Görüntü Dosyası Yükle" (PNG, JPG)
- Gemini API ile analiz edilir

#### **Adım 4: Soru Sor**
**Ana Arama Bölümünde:**
```
Soru: "Thread yönetiminde deadlock'ı nasıl önleyebilirim?"
```

Sistem otomatik olarak:
1. ✅ ChromaDB'de benzer belgeleri bulur
2. ✅ Soruda geçen anahtar kelimeleri analiz eder
3. ✅ Uygun kaynakları seçer (PDF/Ses/Görüntü)
4. ✅ Groq LLM'e göndererek bağlamsal cevap üretir

---

## 📁 Proje Yapısı

```
Multimodal Assistant/
├── main.py                          # 🎯 Ana Streamlit uygulaması
├── requirements.txt                 # 📦 Bağımlılıklar
├── .env                             # 🔐 API Keys (.gitignore'da)
├── depo.py                          # 💾 Ders/Konu yönetimi (JSON)
│
├── multimodal-rag/
│   ├── week1_rag/                  # Hafta 1: Temel RAG
│   │   ├── __init__.py
│   │   ├── ingest_rag.py           # PDF/Ses/Görüntü yükleme
│   │   ├── rag_chain.py            # RAG pipeline (LangChain)
│   │   ├── retriever.py            # ChromaDB arama
│   │   ├── test_groq.py            # Test scripti
│   │   └── chroma_db/              # 🗄️ Vektör veritabanı
│   │       ├── chroma.sqlite3
│   │       └── [metadata folders]
│   │
│   └── week2_multimodal/           # Hafta 2: Ses + Görüntü
│       ├── __init__.py
│       ├── pipeline.py             # 🔄 Multimodal pipeline
│       ├── stt.py                  # Speech-to-Text (Whisper)
│       ├── vision.py               # Image analysis (Gemini)
│       └── data/                   # 📂 Yüklenen dosyalar
│           ├── test.png
│           ├── test.mp4
│           └── [user uploads]
│
├── README.md                        # 📖 Bu dosya
└── .git/                           # Git version control
```

---

## 🔧 Temel Örnekler

### Örnek 1: PDF'ten Soru Sorma
```
Ders: "Veri Tabanları"
Konu: "SQL Sorguları"
Yüklü Dosya: ders_notlari.pdf

Soru: "JOIN operatörü ne işe yarar?"
Cevap: [PDF'den çıkartılan bağlam ile LLM tarafından üretilen detaylı cevap]
```

### Örnek 2: Ses Kaydıyla Öğrenme
```
Ders: "İşletim Sistemleri"
Konu: "Thread Yönetimi"
Yüklü Dosya: ders_dersi.mp3 (hoca kaydı)

Soru: "Deadlock nedir?"
İşlem:
  1. mp3 → Whisper ile metin dönüştürülür
  2. ChromaDB'de arama yapılır
  3. Bağlamsal cevap üretilir + kaynak gösterilir
```

### Örnek 3: Görüntü + Metin Kombinasyonu
```
Ders: "Bilgisayar Mimarisi"
Konu: "İşlemci Tasarımı"
Yüklü Dosya: cpu_diyagrami.png + ders_notlari.pdf

Soru: "Bu diyagramdaki components'lerin işlevini açıkla"
İşlem:
  1. Görüntü Gemini ile analiz edilir
  2. PDF'den ilgili kısımlar bulunur
  3. İkisi birleştirilerek detaylı cevap verilir
```

---

## ⚙️ Gelişmiş Konfigürasyon

### LLM Model Seçimi (`rag_chain.py`)
```python
# Hızlı cevaplar için
llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)

# Daha detaylı cevaplar için
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)
```

### Embedding Model Değiştirme (`ingest_rag.py`)
```python
# Türkçe optimized
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# Çok dillililik için
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)
```

### ChromaDB Arama Parametreleri (`retriever.py`)
```python
# Varsayılan: En benzer 2 belge
retriever = vektor_db.as_retriever(search_kwargs={"k": 2})

# Daha detaylı cevaplar için
retriever = vektor_db.as_retriever(search_kwargs={"k": 5})
```

---

## 🐛 Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| **"ModuleNotFoundError: No module named 'langchain'"** | `pip install -r requirements.txt` |
| **ChromaDB hata: "Cannot connect to database"** | `rm -rf week1_rag/chroma_db` ve yeniden başlat |
| **Groq API hatası** | `.env` dosyasında `GROQ_API_KEY` kontrol et |
| **Whisper ses çevirimi yavaş** | GPU'yu kullan: CUDA kurulu PyTorch kur |
| **Gemini API "quota exceeded"** | Ücretsiz tier limitini aştın → ücretli plan geçişi yap |
| **Streamlit "Port 8501 already in use"** | `streamlit run main.py --server.port 8502` |

---

## 📊 Teknik Detaylar

### Embedding ve Retrieval Akışı
```
Metin Input → Embedding Model (all-MiniLM) → Vektör (384D)
    ↓
ChromaDB İçinde Benzerlik Araması (Cosine Distance)
    ↓
Top-K Belge Seçimi (k=2 varsayılan)
    ↓
LLM'e Bağlam Olarak Gönderme
```

### Multimodal Processing
```
┌─ PDF ────────► Metin
├─ Ses ────────► Whisper STT ──► Metin
└─ Görüntü ────► Gemini Vision ──► Açıklama

    ↓ (Tümü)
    
Birleştirilen Bağlam → LLM → Final Cevap
```

---

## 🚀 İleri Seviye Özellikler

### Kaynak Filtresi (Otomatik)
Soru içeriğine göre arama kaynağı otomatik seçilir:

```
Soru: "Derste hoca ne söyledi?"      → Ses kayıtlarında ara
Soru: "PDF'de yazıyor mu?"            → PDF'lerde ara
Soru: "Diyagramda ne görüyorsun?"    → Görüntülerde ara
```

### Metadata ile Filtreleme
Her belgeye eklenen metadata (ders, konu, kaynak, tarih):
```python
{
    "kaynak": "pdf_dokuman",
    "ders": "Veri Tabanları",
    "konu": "Normalizasyon",
    "tarih": "2024-04-14"
}
```

---

## 📚 Kullanılan Kütüphaneler (Başlıca)

- **LangChain**: RAG framework
- **ChromaDB**: Vektör veritabanı
- **HuggingFace**: Embedding & STT modelleri
- **Groq**: LLM API (ücretsiz)
- **Google Gemini**: Vision API (ücretsiz tier)
- **Streamlit**: Web UI
- **PyPDF**: PDF işleme
- **Librosa**: Ses işleme

---

## 🎓 Eğitim Amaçlı Notlar

Bu proje, aşağıdaki kavramları öğrenmek için uygundur:
- ✅ RAG (Retrieval Augmented Generation) mimarisi
- ✅ Vector embeddings ve similarity search
- ✅ LLM chaining ve prompt engineering
- ✅ Multimodal AI (metin + ses + görüntü)
- ✅ Vektör veritabanları (ChromaDB)
- ✅ Streamlit web uygulamaları

---

## 🤝 Katkıda Bulunma

Geliştirmeler ve hata raporları için pull request gönderin!

---

## 📝 Lisans

Bu proje açık kaynak projesidir. Lütfen kendi projelerinizde kullanmaktan çekinmeyin.

---

## ❓ SSS

**S: Çevrimdışı çalışabilir mi?**
A: Evet! Ollama ile lokal LLM kullanabilirsiniz (Groq API olmadan). Gemini hariç.

**S: Kaç belge tutabilir?**
A: ChromaDB lokal SQLite kullandığı için teorik olarak sınırsız, pratik olarak ~1M belge (~10GB).

**S: Cevaplar neden bazen hatalı?**
A: LLM'ler hallüsinasyon yapabilir. Bağlamda bilgi yoksa "Bu konuda bilgim yok" mesajı verir.

**S: Ses işleme ne kadar hızlı?**
A: 1 dakikalık ses ~2-3 saniye (GPU ile), ~10-15 saniye (CPU ile).

---

**Son Güncelleme:** Mayıs 2026
**Versiyon:** 2.0 (Multimodal RAG)

Sorularınız için GitHub Issues açabilirsiniz! 🚀
