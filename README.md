# 🎓 Akademik Bellek Asistanı (Academic Memory Assistant)

Multimodal RAG (Retrieval Augmented Generation) tabanlı, **Türkçe** akademik yardımcı sistemi. Ders PDF'lerinizi, ses kayıtlarınızı ve görsellerinizi tek bir bellekte toplar; doğal dille sorduğunuz sorulara **yalnızca kendi kaynaklarınıza dayanarak** cevap üretir.

> Materyalleri **ders → konu** hiyerarşisinde organize eder, her konu için ayrı sohbet geçmişi tutar ve cevapların hangi kaynaktan (📄 PDF / 🎤 Ses / 🖼️ Görüntü) geldiğini etiketler.

Proje **iki arayüzle** birlikte gelir:

| | Arayüz | Durum | Nasıl çalışır? |
|---|---|---|---|
| 🌐 | **Next.js + FastAPI + Supabase** (`frontend/`, `backend/`, `supabase/`) | **Güncel / ana ürün** | Çok kullanıcılı, girişli (auth), Supabase Storage + Postgres, SSE ile token token akan cevaplar |
| 🧪 | **Streamlit prototipi** (`main.py`, `multimodal-rag/`) | Referans / tek kullanıcılı | Tek makinede, JSON dosyalarında saklama, giriş yok |

Yeni geliştirme full-stack tarafında yapılır; Streamlit prototipi RAG mantığının okunması kolay hâli olarak repoda durur.

---

## 📋 İçindekiler

- [Proje Nedir?](#-proje-nedir)
- [Özellikler](#-özellikler)
- [Sistem Mimarisi](#️-sistem-mimarisi)
- [Teknoloji Stack'i](#teknoloji-stacki)
- [Gereksinimler](#-gereksinimler)
- [Kurulum (Full-Stack)](#-kurulum-full-stack)
- [Kullanım](#-kullanım)
- [API Uç Noktaları](#-api-uç-noktaları)
- [Streamlit Prototipi](#-streamlit-prototipi)
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

### 🔐 Hesap ve Çok Kullanıcılılık (full-stack)
- **Supabase Auth** ile kayıt/giriş; her kullanıcı yalnızca kendi derslerini görür.
- **RLS politikaları** ve kullanıcı klasörü bazlı storage kuralları veritabanı seviyesinde uygulanır.
- Dosyalar **private Supabase Storage bucket'larında** tutulur (`pdfs`, `audio`, `images`).

### 📚 Organizasyon
- **Ders Yönetimi**: Ders oluştur, adını düzenle, sil.
- **Konu Yönetimi**: Her derse konular ekle; materyaller konu bazında indekslenir.
- **Konu Bazlı Sohbet**: Her ders–konu kombinasyonu kendi sohbet geçmişine ve kaynaklarına sahiptir; konular arası sızma olmaz.
- **Kalıcı Depo**: Full-stack'te Postgres (`courses` / `topics` / `materials` / `chat_messages`); Streamlit prototipinde `dersler.json` + `sohbetler.json`.

### 📥 Çok Kaynaklı Yükleme (Ingest)
- **📄 PDF** (≤ 50 MB): Sayfa sayfa metin çıkarma → parçalama → ChromaDB'ye indeksleme.
- **🎤 Ses** (≤ 100 MB, `mp4 / mp3 / wav / m4a`): **Groq Whisper** ile Türkçe metne çevirme.
- **🖼️ Görüntü** (≤ 10 MB, `png / jpg / jpeg`): **OpenRouter Vision** ile sınıflandırma + detaylı analiz.
- **Yinelenen koruması**: Aynı dosya aynı konuya tekrar yüklenirse eski parçalar silinip yeniden indekslenir.

### 💬 Akıllı Cevaplama
- **Akan cevap (SSE)**: Backend `text/event-stream` ile token token yayınlar; arayüzde cevap yazılırken görünür.
- **Kaynak yönlendirme**: Sorudaki anahtar kelimelere göre (örn. "derste hoca…" → ses, "diyagramda…" → görüntü) ilgili kaynağa öncelik verilir.
- **MMR retrieval**: Tekrar eden parçalar yerine çeşitlilik veren `max_marginal_relevance_search` ile tanım + örnek + uygulama bir arada yakalanır.
- **Etiketli yanıt**: Her bilgi geldiği kaynakla işaretlenir; ilişki/karşılaştırma sorularında ayrı bir sentez paragrafı üretilir.
- **Konuşma hafızası**: Son 5 tur bağlama eklenir; "peki ya bu?" gibi atıflar çözülür.
- **Matematik desteği**: Cevaplardaki LaTeX ifadeleri arayüzde KaTeX ile render edilir.

---

## 🏗️ Sistem Mimarisi

```
┌──────────────────────────────────────────────────────────────┐
│              NEXT.JS FRONTEND (frontend/, App Router)        │
│   Auth · Ders/Konu sayfaları · Materyal paneli · Sohbet      │
└───────┬──────────────────────────────────┬───────────────────┘
        │ Supabase JS (auth + upload)      │ axios / fetch (SSE)
        ▼                                  ▼
┌────────────────────────┐   ┌──────────────────────────────────┐
│  SUPABASE              │   │  FASTAPI BACKEND (backend/app)   │
│  ├─ Auth (JWT)         │◀──│  ├─ middleware/auth.py (JWT)     │
│  ├─ Postgres + RLS     │   │  ├─ routers: courses · topics ·  │
│  │   courses, topics,  │   │  │    materials · chat · health  │
│  │   materials,        │   │  └─ db/repository.py             │
│  │   chat_messages     │   └───────────────┬──────────────────┘
│  └─ Storage (private)  │                   │
│      pdfs/audio/images │                   ▼
└────────────────────────┘   ┌──────────────────────────────────┐
                             │   AI ENGINE (backend/ai_engine)  │
                             │  ingest.py · retriever.py        │
                             │  pipeline.py · stt.py · vision.py│
                             └───────────────┬──────────────────┘
                                             ▼
             ┌───────────────────────────────────────────────────┐
             │        ChromaDB (Lokal Vektör Veritabanı)         │
             │  Embedding: multilingual-MiniLM-L12 (384D)        │
             │  Metadata: ders_id, konu_id, kaynak, dosya, tarih │
             └───────────────────────────────────────────────────┘
```

Dosya yükleme akışı: tarayıcı dosyayı **doğrudan** Supabase Storage'a yükler, ardından backend'e `POST /materials/topics/{id}/materials/process` çağrısı gider; backend dosyayı indirip işler, parçaları ChromaDB'ye yazar ve metadata'yı Postgres'e kaydeder.

### Teknoloji Stack'i

| Bileşen | Teknoloji | Rol |
|---|---|---|
| **Frontend** | Next.js 16 (App Router) + React 19 + TypeScript | Web arayüzü (`frontend/`) |
| **State / HTTP** | Zustand, axios, react-markdown + KaTeX | İstemci durumu, API, markdown/matematik |
| **Backend** | FastAPI + Uvicorn (Python 3.12) | REST API + SSE (`backend/app/`) |
| **Auth & DB & Storage** | Supabase (Postgres + RLS + Auth + Storage) | Kullanıcı, veri ve dosya katmanı |
| **RAG Framework** | LangChain | Pipeline ve prompt yönetimi |
| **Vektör DB** | ChromaDB (`langchain-chroma`) | Belge depolama & benzerlik araması |
| **Embeddings** | HuggingFace `paraphrase-multilingual-MiniLM-L12-v2` | Metin → 384B vektör (çok dilli) |
| **LLM (Cevap)** | Groq — `openai/gpt-oss-120b` | Bağlamsal cevap üretme |
| **Ses → Metin (STT)** | Groq Whisper — `whisper-large-v3-turbo` | Türkçe transkripsiyon |
| **Görüntü Analizi** | OpenRouter — `meta-llama/llama-4-maverick` | Diyagram/görsel analizi (OpenAI SDK ile) |
| **Ses Ön İşleme** | pydub + ffmpeg | Mono/16kHz sıkıştırma |
| **Prototip Arayüz** | Streamlit | Tek kullanıcılı sürüm (`main.py`) |

---

## 📦 Gereksinimler

### Sistem
- **Python 3.10+** (backend `venv`'i 3.12 ile kurulmuştur)
- **Node.js 20+** ve npm (frontend `pnpm` de kullanabilir)
- **ffmpeg** (ses işleme için zorunlu — pydub buna bağlıdır)
- ~2GB disk alanı (embedding modeli + bağımlılıklar)
- İlk kurulumda internet bağlantısı

### API Anahtarları
| Anahtar | Ne için? | Nereden? |
|---|---|---|
| `GROQ_API_KEY` | LLM cevapları **ve** Whisper ses→metin | https://console.groq.com |
| `OPENROUTER_API_KEY` | Görüntü/diyagram analizi | https://openrouter.ai/keys |
| `SUPABASE_*` | Auth, veritabanı, storage (yalnız full-stack) | Supabase Dashboard → Project Settings → API |
| `HF_TOKEN` | Embedding modelini indirmek (opsiyonel) | https://huggingface.co/settings/tokens |

> Groq ve OpenRouter ücretsiz katmanla başlar. Bu projede Google Gemini **kullanılmıyor**; görüntü analizi OpenRouter üzerinden yapılır.

---

## 🚀 Kurulum (Full-Stack)

### 1️⃣ Depoyu klonla
```bash
git clone <repository-url>
cd "Multimodal Assistant"
```

### 2️⃣ Backend sanal ortamı ve bağımlılıklar
```bash
# Windows
python -m venv backend\venv
backend\venv\Scripts\activate

# macOS / Linux
python3 -m venv backend/venv
source backend/venv/bin/activate

pip install -r backend/requirements.txt
```

GPU'n varsa PyTorch'u GPU destekli sürümle değiştirebilirsin:
```bash
# NVIDIA GPU (CUDA 12.1)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 3️⃣ Frontend ve kök bağımlılıkları
```bash
npm install                  # kök: concurrently + supabase CLI
npm run install:frontend     # frontend/ bağımlılıkları (pnpm)
```

### 4️⃣ ffmpeg kur
```bash
# Windows  → https://www.gyan.dev/ffmpeg/builds/ (indir, PATH'e ekle)
# macOS    → brew install ffmpeg
# Ubuntu   → sudo apt-get install ffmpeg
```

> ⚠️ **Not:** Streamlit prototipindeki `multimodal-rag/week2_multimodal/stt.py` içinde ffmpeg yolu sabit (`C:\Users\merve\Desktop\ffmpeg\bin\...`) yazılıdır. Prototipi kendi makinende çalıştırırken bu yolu güncelle veya ffmpeg'i PATH'e ekleyip ilgili satırları kaldır.

### 5️⃣ Ortam değişkenleri
```bash
cp backend/.env.example backend/.env      # Supabase + Groq + OpenRouter anahtarları
cp frontend/.env.example frontend/.env    # NEXT_PUBLIC_SUPABASE_* + NEXT_PUBLIC_API_URL
```

Streamlit prototipi ayrıca proje kökündeki `.env` dosyasını okur (`GROQ_API_KEY`, `OPENROUTER_API_KEY`).

> `backend/app/config.py` varsayılan olarak `backend/.env` dosyasını okur. Başka bir dosyaya geçmek için `ENV_FILE=.env.local` ortam değişkenini ayarlaman yeterli (örn. lokal `supabase start` stack'i için).

### 6️⃣ Supabase (veritabanı, auth, storage)
Şema — tablolar, RLS politikaları, storage bucket'ları — `supabase/migrations/`
altında sürüm kontrolünde tutulur. Kurulum, lokal geliştirme (`npm run db:start`),
şema çekme ve **duraklatılmış projeyi kurtarma** adımları için:
**[supabase/README.md](supabase/README.md)**

> ℹ️ Supabase Free plan, 7 gün istek almayan projeyi otomatik duraklatır.
> `.github/workflows/supabase-keepalive.yml` bunu 3 günde bir ping atarak
> engeller; çalışması için repo secret'ları `SUPABASE_URL` ve `SUPABASE_ANON_KEY`
> tanımlı olmalı.

---

## 💻 Kullanım

### Her ikisini birden başlat
```bash
npm run dev
```
- Frontend → `http://localhost:3000`
- Backend  → `http://localhost:8000` (Swagger: `http://localhost:8000/docs`)

Ayrı ayrı çalıştırmak istersen: `npm run dev:backend` / `npm run dev:frontend`.

| Komut | Ne yapar? |
|---|---|
| `npm run dev` | Backend + frontend'i birlikte (concurrently) başlatır |
| `npm run build:frontend` | Next.js production build |
| `npm run start:frontend` | Build edilmiş frontend'i çalıştırır |
| `npm run db:start` / `db:stop` | Lokal Supabase stack'i aç/kapat |
| `npm run db:reset` | Lokal DB'yi migration'lardan sıfırdan kurar |
| `npm run db:pull` / `db:diff` | Canlı şemayı çek / repo ile farkı gör |

### Temel iş akışı

**1. Hesap aç** — `/register` ile kayıt ol, `/login` ile giriş yap.

**2. Ders oluştur** — Dashboard → *Yeni Ders* → ad gir → *Oluştur*.

**3. Konu ekle** — Dersi aç → *Yeni Konu Ekle* → konu adı → *Konu Oluştur*.

**4. Materyal yükle** — Konuyu aç, materyal panelinden:
- **📄 PDF Ekle** → sayfa sayfa metin çıkarılır, parçalanıp indekslenir
- **🎤 Ses Ekle** → `mp4/mp3/wav/m4a`, Whisper ile Türkçe metne çevrilir
- **🖼️ Görüntü Ekle** → `png/jpg/jpeg`, Vision ile analiz edilir

**5. Soru sor** — Sohbet kutusuna yaz; cevap akarak gelir. İstersen *🖼️ Görüntüyü dahil et* / *🎤 Ses kaydını dahil et* seçenekleriyle aktif kaynağı o soruya kat.

---

## 🔌 API Uç Noktaları

Tümü `/api/v1` ön ekiyle sunulur ve `Authorization: Bearer <supabase-jwt>` başlığı bekler (health hariç). İnteraktif dokümantasyon: `/docs`.

| Metot | Yol | Açıklama |
|---|---|---|
| `GET` | `/health` | Servis sağlığı |
| `GET` / `POST` | `/courses` | Dersleri listele / oluştur |
| `PATCH` / `DELETE` | `/courses/{course_id}` | Ders adını güncelle / sil |
| `GET` / `POST` | `/topics/courses/{course_id}/topics` | Dersin konularını listele / ekle |
| `PATCH` / `DELETE` | `/topics/{topic_id}` | Konu güncelle / sil |
| `GET` | `/materials/topics/{topic_id}/materials` | Konunun materyallerini listele |
| `POST` | `/materials/topics/{topic_id}/materials/process` | Storage'daki dosyayı işle + indeksle |
| `DELETE` | `/materials/{material_id}` | Materyali ve parçalarını sil |
| `POST` | `/chat/topics/{topic_id}/chat` | Soru sor — **SSE** ile akan cevap |
| `GET` / `DELETE` | `/chat/topics/{topic_id}/chat/history` | Sohbet geçmişini getir / temizle |

SSE gövde formatı: `data: {"token": "..."}` satırları, sonunda `data: {"done": true, "sources": {...}}`.

---

## 🧪 Streamlit Prototipi

Tek kullanıcılı, girişsiz sürüm — RAG akışını hızlıca denemek için:

```bash
pip install -r requirements.txt
streamlit run main.py
```
Tarayıcı otomatik açılır → `http://localhost:8501`

Ders/konu yapısı `multimodal-rag/dersler.json`, sohbetler `multimodal-rag/sohbetler.json` içinde saklanır; vektörler `multimodal-rag/week1_rag/chroma_db/` altındadır. Bu sürüm Supabase kullanmaz.

---

## 📁 Proje Yapısı

```
Multimodal Assistant/
├── package.json                     # 🧰 Kök script'ler (dev, build, db:*)
├── README.md                        # 📖 Bu dosya
├── .env                             # 🔐 Prototip anahtarları (.gitignore'da)
│
├── backend/                         # ⚙️ FastAPI servisi
│   ├── requirements.txt
│   ├── .env.example                 # Supabase + AI anahtarları şablonu
│   ├── app/
│   │   ├── main.py                  # FastAPI uygulaması, CORS, router kaydı
│   │   ├── config.py                # Pydantic Settings (model & yol ayarları)
│   │   ├── middleware/auth.py       # Supabase JWT doğrulama
│   │   ├── db/                      # supabase client + repository (CRUD)
│   │   ├── models/                  # Pydantic request/response şemaları
│   │   └── routers/                 # health · courses · topics · materials · chat
│   └── ai_engine/                   # 🧠 RAG çekirdeği (servis sürümü)
│       ├── ingest.py                # PDF/Ses/Görüntü → ChromaDB
│       ├── retriever.py             # MMR tabanlı belge getirme
│       ├── pipeline.py              # Sorgu pipeline'ı (retrieval + LLM)
│       ├── stt.py                   # Ses → Metin (Groq Whisper + pydub)
│       ├── vision.py                # Görüntü analizi (OpenRouter Vision)
│       └── prompts/diyagram_turleri.yaml
│
├── frontend/                        # 🌐 Next.js 16 (App Router)
│   ├── .env.example                 # NEXT_PUBLIC_SUPABASE_* + API URL
│   └── src/
│       ├── app/(auth)/              # login · register
│       ├── app/(dashboard)/         # courses → [courseId] → topics/[topicId]
│       ├── components/chat/         # ChatInterface · MarkdownMessage (KaTeX)
│       ├── components/materials/    # MaterialsSidebar (yükleme paneli)
│       └── lib/                     # api.ts · stream.ts (SSE) · supabase.ts · math.ts
│
├── supabase/                        # 🗄️ Şemanın tek kaynağı
│   ├── config.toml
│   ├── migrations/*.sql             # tablolar, RLS, storage bucket'ları
│   └── README.md                    # kurulum / yedek / duraklatma rehberi
│
├── .github/workflows/               # Supabase keepalive (3 günde bir ping)
├── plan/phases/                     # 📝 Faz faz uygulama planı (1–5)
│
├── main.py                          # 🧪 Streamlit prototipi (arayüz + akış)
├── requirements.txt                 # Prototip bağımlılıkları
└── multimodal-rag/                  # 🧪 Prototip RAG kodu
    ├── depo.py                      # Ders/konu JSON yönetimi (CRUD)
    ├── dersler.json / sohbetler.json
    ├── prompts/diyagram_turleri.yaml
    ├── week1_rag/                   # ingest_rag.py · retriever.py · rag_chain.py · chroma_db/
    └── week2_multimodal/            # pipeline.py · stt.py · vision.py · data/
```

---

## ⚙️ Çalışma Akışı (Teknik)

### Yükleme (ingest)
```
Tarayıcı → Supabase Storage (pdfs / audio / images, private)
        → POST /materials/topics/{id}/materials/process
        → backend dosyayı indirir (TEMP_UPLOAD_DIR), işler, geçici dosyayı siler

PDF      → pypdf ile sayfa metni → RecursiveCharacterTextSplitter (chunk=500/overlap=50)
Ses      → pydub (mono/16kHz) → Groq Whisper (whisper-large-v3-turbo, tr) → metin → chunk
Görüntü  → OpenRouter Vision: (1) tür sınıflandır (2) türe göre detaylı analiz → metin
                        ↓
         multilingual-MiniLM-L12 embedding → ChromaDB (+ metadata: ders_id, konu_id, kaynak, dosya, tarih)
                        ↓
         materials tablosuna kayıt (dosya adı, tür, storage yolu, chunk sayısı)
```

### Sorgu (pipeline.py)
```
Soru → son 5 tur sohbet geçmişi bağlama eklenir
     → kaynak_belirle() (anahtar kelimeyle PDF/Ses/Görüntü yönlendirmesi)
     → konu_id filtresiyle PDF ve Ses bağlamlarını ayrı ayrı MMR ile getir
     → (varsa) aktif görüntüyü anlık analiz et
     → hepsini etiketli prompt'a yerleştir → Groq LLM → topraklanmış cevap
     → SSE ile token token yayınla, tamamlanınca chat_messages'a kaydet
```

### Önemli parametreler
| Parametre | Değer | Nerede? |
|---|---|---|
| Embedding modeli | `paraphrase-multilingual-MiniLM-L12-v2` | `backend/app/config.py`, `ai_engine/retriever.py` |
| Retrieval | MMR, `k=8`, `fetch_k=25` | `config.py` (`RETRIEVAL_K`, `RETRIEVAL_FETCH_K`) |
| Chunk boyutu | 500 karakter / 50 örtüşme | `ai_engine/ingest.py` |
| LLM | `openai/gpt-oss-120b`, `temperature=0`, `max_tokens=1000` | `config.py`, `ai_engine/pipeline.py` |
| Whisper | `whisper-large-v3-turbo`, `language="tr"` | `config.py`, `ai_engine/stt.py` |
| Vision | `meta-llama/llama-4-maverick` | `config.py`, `ai_engine/vision.py` |
| Dosya limitleri | PDF 50 MB · Ses 100 MB · Görüntü 10 MB | `supabase/migrations/*_storage_buckets.sql` |
| CORS | `http://localhost:3000` (varsayılan) | `config.py` (`CORS_ORIGINS`) |

---

## 🐛 Sorun Giderme

| Sorun | Çözüm |
|---|---|
| `ModuleNotFoundError` (backend) | `pip install -r backend/requirements.txt` (doğru venv aktif mi?) |
| ffmpeg / pydub hatası (`Couldn't find ffmpeg`) | ffmpeg'i kur, PATH'e ekle; prototipte `stt.py` içindeki sabit yolu güncelle |
| Groq API hatası | `backend/.env` içinde `GROQ_API_KEY` doğru mu kontrol et |
| Görüntü analizi başarısız | `backend/.env` içinde `OPENROUTER_API_KEY` ekli mi kontrol et |
| `diyagram_turleri.yaml not found` | `backend/ai_engine/prompts/` klasörünün yerinde olduğundan emin ol |
| ChromaDB bozuldu | `backend/ai_engine/chroma_db/` (prototipte `multimodal-rag/week1_rag/chroma_db/`) klasörünü sil ve materyalleri yeniden yükle |
| Frontend'de CORS hatası | `backend/.env` içindeki `CORS_ORIGINS` frontend adresini içeriyor mu? |
| Frontend backend'e bağlanmıyor | `frontend/.env` → `NEXT_PUBLIC_API_URL=http://localhost:8000` |
| Yükleme "storage" hatası veriyor | Dosya türü/boyutu bucket limitlerine uyuyor mu; migration'lar uygulandı mı? |
| Port kullanımda | Backend: `--port 8001` · Frontend: `npm run dev -- -p 3001` · Streamlit: `streamlit run main.py --server.port 8502` |
| Supabase istekleri zaman aşımına uğruyor / proje "paused" | Dashboard'dan **Resume project**; detaylar [supabase/README.md](supabase/README.md) |
| Login çalışıyor ama API 401 dönüyor | `backend/.env` içindeki `SUPABASE_JWT_SECRET` dashboard'daki değerle aynı mı kontrol et |

---

## ❓ SSS

**S: Full-stack mi Streamlit mi kullanmalıyım?**
A: Gerçek kullanım için full-stack sürüm (`npm run dev`) — giriş, çok kullanıcı ve kalıcı bulut depolama orada. Streamlit prototipi RAG akışını hızlı denemek/okumak için.

**S: Cevaplar neden bazen "kaynaklarda bilgi bulunamadı" diyor?**
A: Sistem bilerek topraklanmıştır — yalnızca yüklediğin materyallerde yazan bilgiyi kullanır, uydurmaz. İlgili dosyayı doğru konuya yüklediğinden emin ol.

**S: Aynı PDF'i iki kez yüklersem ne olur?**
A: Eski parçalar otomatik silinip yeniden indekslenir; tekrar (duplikasyon) oluşmaz.

**S: Verilerim nerede duruyor?**
A: Dosyalar private Supabase Storage bucket'larında, ders/konu/sohbet kayıtları RLS korumalı Postgres tablolarında, vektörler ise backend'in yanındaki lokal ChromaDB'de.

**S: Hangi diller destekleniyor?**
A: Arayüz ve cevaplar Türkçe odaklıdır; embedding modeli çok dilli, Whisper Türkçe'ye ayarlıdır.

**S: Google Gemini gerekli mi?**
A: Hayır. Görüntü analizi OpenRouter, ses ve LLM Groq üzerinden çalışır.

**S: İnternetsiz çalışır mı?**
A: Hayır. LLM (Groq), STT (Groq), görüntü (OpenRouter) ve Supabase bulut servisleridir; sadece embedding ve ChromaDB lokaldir.

---

**Versiyon:** 3.0 (Full-Stack Multimodal RAG — Next.js · FastAPI · Supabase)
Sorularınız için GitHub Issues açabilirsiniz. 🚀
