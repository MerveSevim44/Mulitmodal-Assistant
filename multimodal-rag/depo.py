import json
import os

DEPO_DOSYASI = os.path.join(os.path.dirname(__file__), "dersler.json")

def depo_yukle() -> dict:
    """JSON'dan dersleri yükle"""
    if os.path.exists(DEPO_DOSYASI):
        with open(DEPO_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def depo_kaydet(dersler: dict) -> None:
    """Dersleri JSON'a kaydet"""
    with open(DEPO_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(dersler, f, ensure_ascii=False, indent=2)

def ders_ekle(ders_id: str, ders_adi: str) -> None:
    dersler = depo_yukle()
    if ders_id not in dersler:
        dersler[ders_id] = {"id": ders_id, "ad": ders_adi, "konular": {}}
    depo_kaydet(dersler)

def konu_ekle(ders_id: str, konu_id: str, konu_adi: str) -> None:
    dersler = depo_yukle()
    if ders_id in dersler:
        dersler[ders_id]["konular"][konu_id] = {"id": konu_id, "ad": konu_adi}
    depo_kaydet(dersler)

def ders_sil_depo(ders_id: str) -> None:
    dersler = depo_yukle()
    dersler.pop(ders_id, None)
    depo_kaydet(dersler)

def konu_sil_depo(ders_id: str, konu_id: str) -> None:
    dersler = depo_yukle()
    if ders_id in dersler:
        dersler[ders_id]["konular"].pop(konu_id, None)
    depo_kaydet(dersler)