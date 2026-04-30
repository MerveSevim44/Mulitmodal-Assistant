import streamlit as st
import os
import sys
import uuid

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
    background: #13131f;
    border: 1px solid #1e1e30;
    border-radius: 12px;
    padding: 20px;
    margin: 8px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
}
.kart:hover { border-color: #6366f1; }
.kart-adi {
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    color: #e0e0ff;
    font-weight: 600;
}
.kart-meta {
    font-size: 11px;
    color: #6366f1;
    margin-top: 6px;
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
    """ChromaDB'deki tüm ders ve konu bilgilerini çek"""
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

# ── SESSION STATE ───────────────────────────────────────────────

if "aktif_ders_id" not in st.session_state:
    st.session_state.aktif_ders_id = None
if "aktif_konu_id" not in st.session_state:
    st.session_state.aktif_konu_id = None
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = {}
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
        c1, c2 = st.columns([5, 1])
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
            if st.button("🗑", key=f"sil_{ders_id}"):
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
                st.markdown(f"""
                <div class="kart">
                    <div class="kart-adi">📚 {ders_adi}</div>
                    <div class="kart-meta">{konu_sayisi} konu</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Aç", key=f"ana_{ders_id}", use_container_width=True):
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
            with cols[i % 3]:
                st.markdown(f"""
                <div class="kart">
                    <div class="kart-adi">📖 {konu_adi}</div>
                    <div class="kart-meta">
                        {"📄 " + str(pdf_say) if pdf_say else ""}
                        {"🎤 " + str(ses_say) if ses_say else ""}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                c1, c2 = st.columns([4, 1])
                with c1:
                    if st.button("Aç", key=f"konu_{konu_id}", use_container_width=True):
                        st.session_state.aktif_konu_id = konu_id
                        st.rerun()
                with c2:
                    if st.button("🗑", key=f"konu_sil_{konu_id}"):
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

    # Breadcrumb
    st.markdown(f'<div class="breadcrumb">📚 {ders_adi} → 📖 {konu_adi}</div>', unsafe_allow_html=True)

    col_geri1, col_geri2 = st.columns([1, 1])
    with col_geri1:
        if st.button("← Derse Dön"):
            st.session_state.aktif_konu_id = None
            st.session_state.aktif_goruntu = None
            st.rerun()
    with col_geri2:
        if st.button("🏠 Ana Sayfa"):
            st.session_state.aktif_ders_id = None
            st.session_state.aktif_konu_id = None
            st.rerun()

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
            if st.button("PDF'i Sisteme Ekle", use_container_width=True, key="pdf_ekle"):
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
            if st.button("Ses'i Sisteme Ekle", use_container_width=True, key="ses_ekle"):
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
            yol = gecici_kaydet(goruntu_dosya, goruntu_dosya.name)
            st.session_state.aktif_goruntu = yol
            st.image(goruntu_dosya, caption="Aktif görüntü", use_container_width=True)
            if st.button("Görüntüyü Sisteme Ekle", key="goruntu_ekle"):
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
        if mesaj_key not in st.session_state.mesajlar:
            st.session_state.mesajlar[mesaj_key] = []

        for mesaj in st.session_state.mesajlar[mesaj_key]:
            with st.chat_message(mesaj["rol"]):
                st.markdown(mesaj["icerik"])

        goruntu_kullan = False
        ses_kullan = False

        if st.session_state.aktif_goruntu or st.session_state.aktif_ses:
            st.markdown('<div class="section-label">// Bu soruda kullan</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.session_state.aktif_goruntu:
                    goruntu_kullan = st.checkbox("🖼️ Görüntüyü dahil et", value=False, key=f"g_{mesaj_key}")
                    st.session_state[f"goruntu_kullan_{mesaj_key}"] = goruntu_kullan
            with c2:
                if st.session_state.aktif_ses:
                    ses_kullan = st.checkbox("🎤 Ses kaydını dahil et", value=False, key=f"s_{mesaj_key}")
                    st.session_state[f"ses_kullan_{mesaj_key}"] = ses_kullan

        soru = st.chat_input(f"{konu_adi} hakkında bir şey sor...")

        if soru:
            with st.chat_message("user"):
                st.markdown(soru)
            st.session_state.mesajlar[mesaj_key].append({"rol": "user", "icerik": soru})

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
                    cevap = pipeline(girdi)
                st.markdown(cevap)

            st.session_state.mesajlar[mesaj_key].append({"rol": "assistant", "icerik": cevap})

        if st.session_state.mesajlar.get(mesaj_key):
            if st.button("🗑️ Sohbeti Temizle"):
                st.session_state.mesajlar[mesaj_key] = []
                st.rerun()