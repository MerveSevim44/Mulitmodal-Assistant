import streamlit as st
import os
import sys
import uuid
import json

PROJE_KLASORU = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJE_KLASORU, "multimodal-rag"))

from week2_multimodal.pipeline import pipeline
from week1_rag.ingest_rag import pdf_yukle, ses_yukle, goruntu_yukle
from week1_rag.retriever import vektor_db
from depo import depo_yukle, ders_ekle, konu_ekle, ders_sil_depo, konu_sil_depo, depo_kaydet

st.set_page_config(
    page_title="Akademik Bellek Asistanı",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Outfit:wght@300;400;500;600&display=swap');

* { font-family: 'Outfit', sans-serif; }

section[data-testid="stSidebar"] {
    background: #0d0d14 !important;
    border-right: 1px solid #1e1e2e;
}
.main .block-container { 
    background: #0a0a10;
    padding: 2rem;
}
.kart {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 2px solid #6366f1;
    border-radius: 12px;
    padding: 20px;
    margin: 8px;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
    display: block;
    width: 100%;
    text-decoration: none;
}
.kart:hover { 
    border-color: #818cf8;
    box-shadow: 0 8px 20px rgba(99, 102, 241, 0.25);
    transform: translateY(-2px);
}
.kart-adi {
    font-family: 'JetBrains Mono', monospace;
    font-size: 16px;
    color: #e0e0ff;
    font-weight: 600;
    margin: 0;
    display: block;
}
.kart-meta {
    font-size: 12px;
    color: #818cf8;
    margin-top: 8px;
    display: block;
    opacity: 0.9;
}
.ders-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #6366f1;
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 24px;
}
.ders-header h2 { color: #e0e0ff; font-size: 24px; font-weight: 600; margin: 0; }
.ders-header p { color: #6366f1; font-size: 12px; font-family: 'JetBrains Mono', monospace; letter-spacing: 0.1em; text-transform: uppercase; margin: 4px 0 0 0; }
.section-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: #6366f1;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin: 16px 0 8px 0;
    border-left: 2px solid #6366f1;
    padding-left: 8px;
}
.breadcrumb {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #6366f1;
    margin-bottom: 16px;
}
button[kind="secondary"] {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%) !important;
    border: 2px solid #6366f1 !important;
    border-radius: 12px !important;
    color: #e0e0ff !important;
    font-weight: 600 !important;
    padding: 20px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15) !important;
}
button[kind="secondary"]:hover {
    border-color: #818cf8 !important;
    box-shadow: 0 8px 20px rgba(99, 102, 241, 0.25) !important;
    transform: translateY(-2px) !important;
}
[data-testid="stFileUploadDropzone"] {
    padding: 12px 16px !important;
    border-radius: 8px !important;
}
[data-testid="stFileUploadDropzone"] p {
    font-size: 12px !important;
    margin: 0 !important;
}
[data-testid="stFileUploadDropzone"] button {
    padding: 8px 16px !important;
    font-size: 12px !important;
    height: auto !important;
}
button {
    font-size: 13px !important;
    padding: 10px 16px !important;
    height: 44px !important;
    min-height: 44px !important;
    max-height: 44px !important;
}
[data-testid="stSidebar"] button {
    height: 48px !important;
    min-height: 48px !important;
    max-height: 48px !important;
}
button[kind="primary"], button[kind="secondary"] {
    height: 44px !important;
    min-height: 44px !important;
}



</style>
""", unsafe_allow_html=True)

# ── YARDIMCI FONKSİYONLAR ──────────────────────────────────────

DATA_KLASORU = os.path.join(PROJE_KLASORU, "multimodal-rag", "week2_multimodal", "data")

def gecici_kaydet(dosya, isim):
    yol = os.path.join(DATA_KLASORU, isim)
    with open(yol, "wb") as f:
        f.write(dosya.getbuffer())
    return yol

def chromadan_yukle():
    """ChromaDB'deki tüm ders ve konu bilgilerini çekiyor ve düzenli bir sözlük yapısında döndürüyor."""
    try:
        sonuclar = vektor_db.get(include=["metadatas", "ids"])
        dersler = {}
        for i, meta in enumerate(sonuclar["metadatas"]):
            ders_id = meta.get("ders_id", "")
            ders_adi = meta.get("ders_adi", "Bilinmeyen")
            konu_id = meta.get("konu_id", "")
            konu_adi = meta.get("konu_adi", "")
            kaynak = meta.get("kaynak", "")
            dosya = meta.get("dosya", "")
            doc_id = sonuclar["ids"][i]

            if not ders_id:
                continue

            if ders_id not in dersler:
                dersler[ders_id] = {
                    "ad": ders_adi,
                    "id": ders_id,
                    "konular": {},
                    "pdf": {},
                    "ses": {}
                }

            # Konu varsa
            if konu_id:
                if konu_id not in dersler[ders_id]["konular"]:
                    dersler[ders_id]["konular"][konu_id] = {
                        "ad": konu_adi,
                        "id": konu_id,
                        "pdf": {},
                        "ses": {},
                        "goruntu": {}
                    }
                konu = dersler[ders_id]["konular"][konu_id]
                if dosya:
                    if kaynak == "pdf_dokuman":
                        konu["pdf"][dosya] = True
                    elif kaynak == "ses_kaydi":
                        konu["ses"][dosya] = True
                    elif kaynak == "goruntu":
                        konu["goruntu"][dosya] = True
            else:
                # Konusuz materyal
                if dosya:
                    if kaynak == "pdf_dokuman":
                        dersler[ders_id]["pdf"][dosya] = True
                    elif kaynak == "ses_kaydi":
                        dersler[ders_id]["ses"][dosya] = True

        return dersler
    except:
        return {}

def dosya_sil(ders_id, dosya_adi, kaynak_tip, konu_id=None):
    try:
        sonuclar = vektor_db.get(include=["metadatas", "ids"])
        silinecek = []
        for i, meta in enumerate(sonuclar["metadatas"]):
            if (meta.get("ders_id") == ders_id and
                meta.get("dosya") == dosya_adi and
                meta.get("kaynak") == kaynak_tip):
                if konu_id is None or meta.get("konu_id") == konu_id:
                    silinecek.append(sonuclar["ids"][i])
        if silinecek:
            vektor_db.delete(ids=silinecek)
        return len(silinecek)
    except Exception as e:
        st.error(f"Silme hatası: {e}")
        return 0

def ders_sil(ders_id):
    try:
        sonuclar = vektor_db.get(include=["metadatas", "ids"])
        silinecek = [sonuclar["ids"][i] for i, m in enumerate(sonuclar["metadatas"]) if m.get("ders_id") == ders_id]
        if silinecek:
            vektor_db.delete(ids=silinecek)
        return len(silinecek)
    except Exception as e:
        st.error(f"Silme hatası: {e}")
        return 0

def konu_sil(konu_id):
    try:
        sonuclar = vektor_db.get(include=["metadatas", "ids"])
        silinecek = [sonuclar["ids"][i] for i, m in enumerate(sonuclar["metadatas"]) if m.get("konu_id") == konu_id]
        if silinecek:
            vektor_db.delete(ids=silinecek)
        return len(silinecek)
    except Exception as e:
        st.error(f"Silme hatası: {e}")
        return 0

# ── SOHBET FONKSIYONLARI ────────────────────────────────────────

SOHBETLER_DOSYASI = os.path.join(PROJE_KLASORU, "multimodal-rag", "sohbetler.json")

def sohbetleri_yukle():
    """Tüm sohbetleri JSON dosyasından yükle"""
    try:
        if os.path.exists(SOHBETLER_DOSYASI):
            with open(SOHBETLER_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return {}

def sohbetleri_kaydet(sohbetler):
    """Sohbetleri JSON dosyasına kaydet"""
    try:
        with open(SOHBETLER_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(sohbetler, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Sohbet kaydetme hatası: {e}")

def sohbet_yukle(ders_id, konu_id):
    """Belirli ders-konu kombinasyonunun sohbetini yükle"""
    sohbetler = sohbetleri_yukle()
    mesaj_key = f"{ders_id}_{konu_id}"
    return sohbetler.get(mesaj_key, [])

def sohbet_kaydet(ders_id, konu_id, mesajlar):
    """Belirli ders-konu kombinasyonunun sohbetini kaydet"""
    sohbetler = sohbetleri_yukle()
    mesaj_key = f"{ders_id}_{konu_id}"
    sohbetler[mesaj_key] = mesajlar
    sohbetleri_kaydet(sohbetler)

def sohbet_sil(ders_id, konu_id):
    """Belirli ders-konu kombinasyonunun sohbetini sil"""
    sohbetler = sohbetleri_yukle()
    mesaj_key = f"{ders_id}_{konu_id}"
    if mesaj_key in sohbetler:
        del sohbetler[mesaj_key]
        sohbetleri_kaydet(sohbetler)

def sohbetteki_kaynaklar_yukle(ders_id, konu_id):
    """Sohbette kullanılan kaynakları yükle"""
    mesajlar = sohbet_yukle(ders_id, konu_id)
    kaynaklar = {"goruntu": None, "ses": None}
    
    # Sohbetteki son kaynakları bul
    for mesaj in reversed(mesajlar):
        if not kaynaklar["goruntu"] and "goruntu" in mesaj:
            kaynaklar["goruntu"] = mesaj.get("goruntu")
        if not kaynaklar["ses"] and "ses" in mesaj:
            kaynaklar["ses"] = mesaj.get("ses")
        if kaynaklar["goruntu"] and kaynaklar["ses"]:
            break
    
    return kaynaklar

# ── SESSION STATE ───────────────────────────────────────────────

if "aktif_ders_id" not in st.session_state:
    st.session_state.aktif_ders_id = None
if "aktif_konu_id" not in st.session_state:
    st.session_state.aktif_konu_id = None
if "aktif_goruntu" not in st.session_state:
    st.session_state.aktif_goruntu = None
if "aktif_ses" not in st.session_state:
    st.session_state.aktif_ses = None

# ChromaDB'den materyal bilgilerini yükle
db_dersler = chromadan_yukle()

# JSON'dan ders/konu yapısını yükle — kalıcı
json_dersler = depo_yukle()

# İkisini birleştir
tum_dersler = {}
for ders_id, ders_info in json_dersler.items():
    tum_dersler[ders_id] = {
        "id": ders_id,
        "ad": ders_info.get("ad", ders_id),
        "konular": {},
        "pdf": db_dersler.get(ders_id, {}).get("pdf", {}),
        "ses": db_dersler.get(ders_id, {}).get("ses", {})
    }
    # Konuları JSON'dan al, ChromaDB materyal bilgisini ekle
    for konu_id, konu_info in ders_info.get("konular", {}).items():
        db_konu = db_dersler.get(ders_id, {}).get("konular", {}).get(konu_id, {})
        tum_dersler[ders_id]["konular"][konu_id] = {
            "id": konu_id,
            "ad": konu_info.get("ad", konu_id),
            "pdf": db_konu.get("pdf", {}),
            "ses": db_konu.get("ses", {}),
            "goruntu": db_konu.get("goruntu", {})
        }

# ChromaDB'de olan ama JSON'da olmayan dersleri de ekle
for ders_id, ders_info in db_dersler.items():
    if ders_id not in tum_dersler:
        tum_dersler[ders_id] = ders_info

# ── SIDEBAR ─────────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="section-label">Akademik Bellek</div>', unsafe_allow_html=True)

    if st.button("🏠 Ana Sayfa", use_container_width=True):
        st.session_state.aktif_ders_id = None
        st.session_state.aktif_konu_id = None
        st.session_state.aktif_goruntu = None
        st.rerun()

    st.divider()

    with st.expander("➕ Yeni Ders"):
        yeni_ders_adi = st.text_input("Ders adı", key="yeni_ders_input",
                                       label_visibility="collapsed", placeholder="örn: Veri Yapıları")
        if st.button("Oluştur", use_container_width=True, key="ders_olustur") and yeni_ders_adi.strip():
            yeni_id = f"ders_{uuid.uuid4().hex[:8]}"
            ders_ekle(yeni_id, yeni_ders_adi.strip())
            st.session_state.aktif_ders_id = yeni_id
            st.session_state.aktif_konu_id = None
            st.rerun()

    st.markdown('<div class="section-label">Derslerim</div>', unsafe_allow_html=True)

    for ders_id, ders_info in tum_dersler.items():
        ders_adi = ders_info.get("ad", ders_id)
        aktif = st.session_state.aktif_ders_id == ders_id
        c1, c2 = st.columns([4.5, 0.8])
        with c1:
            if st.button(
                f"{'▶ ' if aktif else ''}{ders_adi}",
                key=f"sidebar_{ders_id}",
                use_container_width=True,
                type="primary" if aktif else "secondary"
            ):
                st.session_state.aktif_ders_id = ders_id
                st.session_state.aktif_konu_id = None
                st.session_state.aktif_goruntu = None
                st.rerun()
        with c2:
            if st.button("🗑", key=f"sil_{ders_id}", use_container_width=True):
                st.session_state[f"onay_{ders_id}"] = True
                st.rerun()

        if st.session_state.get(f"onay_{ders_id}"):
            st.warning(f"**{ders_adi}** silinsin mi?")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("Evet", key=f"evet_{ders_id}"):
                    ders_sil(ders_id)          # ChromaDB'den sil
                    ders_sil_depo(ders_id)     # JSON'dan sil
                    if st.session_state.aktif_ders_id == ders_id:
                        st.session_state.aktif_ders_id = None
                    st.session_state.pop(f"onay_{ders_id}", None)
                    st.rerun()
            with cc2:
                if st.button("Hayır", key=f"hayir_{ders_id}"):
                    st.session_state.pop(f"onay_{ders_id}", None)
                    st.rerun()

# ── ANA SAYFA ───────────────────────────────────────────────────

if st.session_state.aktif_ders_id is None:
    st.markdown("## 🎓 Akademik Bellek Asistanı")
    st.markdown("Derslerini seç veya yeni ders oluştur.")
    st.divider()

    if tum_dersler:
        st.markdown('<div class="section-label">// Derslerim</div>', unsafe_allow_html=True)
        cols = st.columns(3)
        for i, (ders_id, ders_info) in enumerate(tum_dersler.items()):
            ders_adi = ders_info.get("ad", ders_id)
            konu_sayisi = len(ders_info.get("konular", {}))
            with cols[i % 3]:
                if st.button(f"📚\n{ders_adi}\n{konu_sayisi} konu", 
                            key=f"ana_{ders_id}", 
                            use_container_width=True,
                            help="Derse git"):
                    st.session_state.aktif_ders_id = ders_id
                    st.session_state.aktif_konu_id = None
                    st.rerun()
    else:
        st.info("Henüz ders yok. Sol panelden yeni ders oluştur.")

# ── DERS SAYFASI ────────────────────────────────────────────────

elif st.session_state.aktif_ders_id and st.session_state.aktif_konu_id is None:
    ders_id = st.session_state.aktif_ders_id
    ders_info = tum_dersler.get(ders_id, {})
    ders_adi = ders_info.get("ad", ders_id)
    konular = ders_info.get("konular", {})

    st.markdown(f"""
    <div class="ders-header">
        <p>// aktif ders</p>
        <h2>📚 {ders_adi}</h2>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("✏️ Ders Adını Düzenle"):
            yeni_ad = st.text_input("Yeni ad", value=ders_adi, key="ders_ad_duzenle")
            if st.button("Kaydet", key="ders_ad_kaydet") and yeni_ad.strip() != ders_adi:
                try:
                    # ChromaDB'de güncelle
                    sonuclar = vektor_db.get(include=["metadatas", "ids"])
                    guncelle_ids = []
                    guncelle_metalar = []
                    for i, meta in enumerate(sonuclar["metadatas"]):
                        if meta.get("ders_id") == ders_id:
                            guncelle_ids.append(sonuclar["ids"][i])
                            yeni_meta = meta.copy()
                            yeni_meta["ders_adi"] = yeni_ad.strip()
                            guncelle_metalar.append(yeni_meta)
                    if guncelle_ids:
                        vektor_db.update(ids=guncelle_ids, metadatas=guncelle_metalar)

                    # JSON'da güncelle
                    dersler = depo_yukle()
                    if ders_id in dersler:
                        dersler[ders_id]["ad"] = yeni_ad.strip()
                        depo_kaydet(dersler)

                    st.success("Güncellendi!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Hata: {e}")
    st.divider()

    # Yeni konu ekle
    st.markdown('<div class="section-label">// Konular</div>', unsafe_allow_html=True)
    with st.expander("➕ Yeni Konu Ekle"):
        yeni_konu_adi = st.text_input("Konu adı", key="yeni_konu_input",
                                       label_visibility="collapsed", placeholder="örn: Linked List")
        
        if st.button("Konu Oluştur", use_container_width=True) and yeni_konu_adi.strip():
            yeni_konu_id = f"konu_{uuid.uuid4().hex[:8]}"
            konu_ekle(ders_id, yeni_konu_id, yeni_konu_adi.strip())  # JSON'a kaydet
            st.rerun()

    # Manuel konuları birleştir — artık JSON'dan geliyor
    tum_konular = ders_info.get("konular", {})

    if tum_konular:
        cols = st.columns(3)
        for i, (konu_id, konu_info) in enumerate(tum_konular.items()):
            konu_adi = konu_info.get("ad", konu_id)
            pdf_say = len(konu_info.get("pdf", {}))
            ses_say = len(konu_info.get("ses", {}))
            meta_text = ""
            if pdf_say:
                meta_text += f"📄 {pdf_say} "
            if ses_say:
                meta_text += f"🎤 {ses_say}"
            
            with cols[i % 3]:
                col_btn, col_del = st.columns([5, 1])
                with col_btn:
                    if st.button(f"📖\n{konu_adi}\n{meta_text.strip()}", 
                                key=f"konu_{konu_id}", 
                                use_container_width=True,
                                help="Konuyu aç"):
                        st.session_state.aktif_konu_id = konu_id
                        st.rerun()
                with col_del:
                    if st.button("🗑", key=f"konu_sil_{konu_id}", use_container_width=True):
                        konu_sil(konu_id)                    # ChromaDB'den sil
                        konu_sil_depo(ders_id, konu_id)      # JSON'dan sil
                        st.rerun()
    else:
        st.info("Henüz konu yok. Yukarıdan yeni konu ekle.")

# ── KONU SAYFASI ────────────────────────────────────────────────

elif st.session_state.aktif_ders_id and st.session_state.aktif_konu_id:
    ders_id = st.session_state.aktif_ders_id
    konu_id = st.session_state.aktif_konu_id
    ders_info = tum_dersler.get(ders_id, {})
    ders_adi = ders_info.get("ad", ders_id)


    tum_konular = ders_info.get("konular", {})
    konu_info = tum_konular.get(konu_id, {})
    konu_adi = konu_info.get("ad", konu_id)

    # Konu DEĞİŞTİĞİNDE panel kaynaklarını sıfırla ve yalnızca bu konunun
    # geçmişinden geri yükle. Her rerun'da değil; aksi halde yeni yüklenen
    # görseli eski görselle ezer (clobber) ve konular arası sızma olur.
    if st.session_state.get("_panel_konu_id") != konu_id:
        st.session_state._panel_konu_id = konu_id
        st.session_state.aktif_goruntu = None
        st.session_state.aktif_ses = None
        eski_kaynaklar = sohbetteki_kaynaklar_yukle(ders_id, konu_id)
        if eski_kaynaklar["goruntu"] and os.path.exists(eski_kaynaklar["goruntu"]):
            st.session_state.aktif_goruntu = eski_kaynaklar["goruntu"]
        if eski_kaynaklar["ses"] and os.path.exists(eski_kaynaklar["ses"]):
            st.session_state.aktif_ses = eski_kaynaklar["ses"]

    # Breadcrumb
    st.markdown(f'<div class="breadcrumb">📚 {ders_adi} → 📖 {konu_adi}</div>', unsafe_allow_html=True)

    col_geri1, col_geri2 = st.columns([1, 1])
    with col_geri1:
        if st.button("← Derse Dön", use_container_width=True):
            st.session_state.aktif_konu_id = None
            st.session_state.aktif_goruntu = None
            st.session_state._panel_konu_id = None
            st.rerun()
    with col_geri2:
        if st.button("🏠 Ana Sayfa", use_container_width=True):
            st.session_state.aktif_ders_id = None
            st.session_state.aktif_konu_id = None
            st.session_state._panel_konu_id = None
            st.rerun()

    with st.expander("✏️ Konu Adını Düzenle"):
        yeni_konu_ad = st.text_input("Yeni ad", value=konu_adi, key="konu_ad_duzenle")
        if st.button("Kaydet", key="konu_ad_kaydet") and yeni_konu_ad.strip() != konu_adi:
            if konu_guncelle(ders_id, konu_id, yeni_konu_ad.strip()):
                st.success("Güncellendi!")
                st.rerun()
    st.divider()

    st.markdown(f"""
    <div class="ders-header">
        <p>// aktif konu</p>
        <h2>📖 {konu_adi}</h2>
    </div>
    """, unsafe_allow_html=True)

    yukle_col, sohbet_col = st.columns([1, 2])

    with yukle_col:
        st.markdown('<div class="section-label">📄 PDF Ekle</div>', unsafe_allow_html=True)
        pdf_dosya = st.file_uploader("", type=["pdf"], key=f"pdf_{konu_id}", label_visibility="collapsed")
        if pdf_dosya:
            if st.button("PDF Ekle", use_container_width=True, key="pdf_ekle"):
                with st.spinner("PDF okunuyor..."):
                    yol = gecici_kaydet(pdf_dosya, pdf_dosya.name)
                    pdf_yukle(yol, ders_adi, ders_id, konu_adi, konu_id)
                st.success("✅ Eklendi!")
                st.rerun()

        st.divider()

        st.markdown('<div class="section-label">🎤 Ses Ekle</div>', unsafe_allow_html=True)
        ses_dosya = st.file_uploader("", type=["mp4", "mp3", "wav", "m4a"],
                                      key=f"ses_{konu_id}", label_visibility="collapsed")
        if ses_dosya:
            if st.button("Ses Ekle", use_container_width=True, key="ses_ekle"):
                with st.spinner("Ses metne çevriliyor..."):
                    yol = gecici_kaydet(ses_dosya, ses_dosya.name)
                    ses_yukle(yol, ders_adi, ders_id, konu_adi, konu_id)
                    st.session_state.aktif_ses = yol
                st.success("✅ Eklendi!")
                st.rerun()

        st.divider()

        st.markdown('<div class="section-label">🖼️ Görüntü Ekle</div>', unsafe_allow_html=True)
        goruntu_dosya = st.file_uploader("", type=["png", "jpg", "jpeg"],
                                          key=f"goruntu_{konu_id}", label_visibility="collapsed")
        if goruntu_dosya:
            id_key = f"son_goruntu_id_{konu_id}"
            yol_key = f"goruntu_yol_{konu_id}"
            # Dosyayı yalnızca YENİ seçildiğinde (file_id değişince) işle.
            # Böylece rerun'larda aktif_goruntu koşulsuz yeniden set edilmez;
            # "Kaldır" kalıcı olur ve yeni görsel panele anında yansır.
            if st.session_state.get(id_key) != goruntu_dosya.file_id:
                st.session_state[yol_key] = gecici_kaydet(goruntu_dosya, goruntu_dosya.name)
                st.session_state[id_key] = goruntu_dosya.file_id
                st.session_state.aktif_goruntu = st.session_state[yol_key]
            yol = st.session_state[yol_key]
            st.image(goruntu_dosya, caption="Aktif görüntü", use_container_width=True)
            if st.button("Görüntüyü Ekle", use_container_width=True, key="goruntu_ekle"):
                with st.spinner("Görüntü analiz ediliyor..."):
                    goruntu_yukle(yol, ders_adi, ders_id, konu_adi, konu_id)
                st.success("✅ Eklendi!")
                st.rerun()
            if st.button("🗑 Görüntüyü Kaldır"):
                st.session_state.aktif_goruntu = None
                st.rerun()

    with sohbet_col:
        st.markdown('<div class="section-label">💬 Asistanla Konuş</div>', unsafe_allow_html=True)

        mesaj_key = f"{ders_id}_{konu_id}"
        # JSON'dan sohbeti yükle
        mesajlar = sohbet_yukle(ders_id, konu_id)

        for mesaj in mesajlar:
            with st.chat_message(mesaj["rol"]):
                st.markdown(mesaj["icerik"])

        goruntu_kullan = False
        ses_kullan = False

        if st.session_state.aktif_goruntu or st.session_state.aktif_ses:
            st.markdown('<div class="section-label">// Bu soruda kullan</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.session_state.aktif_goruntu:
                    st.caption("📸 Aktif Görüntü:")
                    st.image(st.session_state.aktif_goruntu, use_container_width=True)
                    goruntu_kullan = st.checkbox("🖼️ Görüntüyü dahil et", value=False, key=f"g_{mesaj_key}")
            with c2:        
             ses_kullan = st.checkbox("🎤 Ses kaydını dahil et", value=False, key=f"s_{mesaj_key}")         

    soru = st.chat_input(f"{konu_adi} hakkında bir şey sor...")

    if soru:
            with st.chat_message("user"):
                st.markdown(soru)
            
            # Kullanıcı mesajını kaynakları ile birlikte JSON'a kaydet
            kullanici_mesaj = {"rol": "user", "icerik": soru}
            if goruntu_kullan and st.session_state.aktif_goruntu:
                kullanici_mesaj["goruntu"] = st.session_state.aktif_goruntu
            if ses_kullan and st.session_state.aktif_ses:
                kullanici_mesaj["ses"] = st.session_state.aktif_ses
            mesajlar.append(kullanici_mesaj)
            sohbet_kaydet(ders_id, konu_id, mesajlar)

            with st.chat_message("assistant"):
                with st.spinner("Düşünüyor..."):
                    girdi = {
                        "soru": soru,
                        "ders_id": ders_id,
                        "konu_id": konu_id
                    }
                    if goruntu_kullan and st.session_state.aktif_goruntu:
                        girdi["goruntu"] = st.session_state.aktif_goruntu
                    if ses_kullan and st.session_state.aktif_ses:
                        girdi["ses"] = st.session_state.aktif_ses

                    # Konuşma geçmişi konu bazlı; rerun'larda korunur, konular sızmaz.
                    gecmis_key = f"gecmis_{konu_id}"
                    if gecmis_key not in st.session_state:
                        st.session_state[gecmis_key] = []
                    gecmis = st.session_state[gecmis_key]

                    # Liste mutable: pipeline içinde bu tur append edilir.
                    cevap = pipeline(girdi, gecmis)
                    # Emin olmak için aynı listeyi session_state'e geri yaz.
                    st.session_state[gecmis_key] = gecmis
                st.markdown(cevap)

            # Asistan mesajını JSON'a kaydet
            mesajlar.append({"rol": "assistant", "icerik": cevap})
            sohbet_kaydet(ders_id, konu_id, mesajlar)
            st.rerun()

    if mesajlar:
            if st.button("🗑️ Temizle", use_container_width=True):
                sohbet_sil(ders_id, konu_id)
                st.session_state[f"gecmis_{konu_id}"] = []
                st.rerun()