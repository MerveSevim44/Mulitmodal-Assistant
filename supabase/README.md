# Supabase — Şema, Yedek ve Duraklatma Rehberi

Bu klasör veritabanı şemasının **tek kaynağı**dır. Tablolar, RLS politikaları ve
storage bucket'ları buradaki migration dosyalarından yeniden kurulabilir; artık
dashboard'daki canlı projeye bağımlı değiliz.

```
supabase/
  config.toml           # supabase init çıktısı (commit edilir)
  migrations/*.sql      # şema geçmişi (commit edilir)
```

Yardımcı komutlar kök `package.json` içinde: `db:start`, `db:stop`, `db:reset`,
`db:pull`, `db:diff`.

---

## 1. Proje duraklatıldıysa

Free plan, **7 gün** istek almayan projeyi otomatik duraklatır. Veri kaybolmaz.

1. Dashboard → **Resume project**. Ücretsiz, birkaç dakika sürer.
2. **Download backups** ile DB dump'ını ve storage objelerini indir. Dump'ı
   **repo dışında** sakla — içinde kullanıcı verisi olabilir.
3. Anahtarları doğrula: Project Settings → API. Proje ref'i ve anahtarlar
   duraklama sonrası değişmez; ama JWT secret rotate edildiyse
   `backend/app/middleware/auth.py` doğrulaması başarısız olur.

Duraklamanın tekrarını **`.github/workflows/supabase-keepalive.yml`** engeller —
3 günde bir REST API'ye hafif bir istek atar. Çalışması için repo secret'ları
gerekir: `SUPABASE_URL` ve `SUPABASE_ANON_KEY` (service_role key **asla**).

> GitHub, 60 gün commit almayan repolarda zamanlanmış workflow'ları devre dışı
> bırakır. Repo uzun süre sessiz kalırsa Actions sekmesinden yeniden etkinleştir.

---

## 2. Canlı şemayı repoya çekmek (bir kereye mahsus)

Proje resume edildikten sonra:

```bash
npx supabase login
npx supabase link --project-ref <proje-ref>   # URL'deki https://<ref>.supabase.co
npm run db:pull                               # -> migrations/<ts>_remote_schema.sql
```

`db:pull`, `courses` / `topics` / `materials` / `chat_messages` tablolarını,
foreign key'leri ve RLS politikalarını yeni bir migration dosyasına yazar.

**Storage bucket'ları bu çıktıya dahil olmaz** — onlar elle yazılmış
`20260904090000_storage_buckets.sql` içinde duruyor. Pull sonrası dashboard'daki
gerçek bucket ayarlarıyla (boyut limitleri, MIME türleri, policy'ler)
karşılaştırıp farklıysa o dosyayı güncelle.

Ardından `npm run db:diff` çıktısının **boş** gelmesi gerekir; boş değilse repo
ile canlı proje arasında yakalanmamış bir fark var demektir.

---

## 3. Lokal geliştirme (Docker gerekir)

Bulut projesine hiç dokunmadan çalışmak için:

```bash
npm run db:start     # lokal Postgres + Auth + Storage; URL ve anahtarları yazdırır
npm run db:reset     # migrations/ dosyalarını sıfırdan uygular
```

CLI'ın yazdırdığı `API URL`, `anon key`, `service_role key` ve `JWT secret`
değerlerini `backend/.env.local` içine koy, sonra backend'i şöyle başlat:

```bash
ENV_FILE=.env.local npm run dev:backend        # PowerShell: $env:ENV_FILE=".env.local"
```

`backend/app/config.py`, `ENV_FILE` ortam değişkeni ile hangi env dosyasını
okuyacağını seçer; değişken yoksa varsayılan `backend/.env` kullanılır.

Bitirince `npm run db:stop`.

---

## 4. Sıfırdan yeni bir bulut projesi kurmak

Mevcut proje kalıcı olarak kaybolursa:

```bash
npx supabase link --project-ref <yeni-ref>
npx supabase db push        # migrations/ içindekileri uzak projeye uygular
```

Sonra `backend/.env` ve frontend env dosyalarındaki URL/anahtarları yenile.
Kullanıcı verisi için elindeki dump'ı restore et.
