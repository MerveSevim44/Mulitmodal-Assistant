from retriever import vektor_db
from collections import Counter

# Tüm dökümanları al
hepsi = vektor_db.get()  # {"ids": [...], "documents": [...], "metadatas": [...]}

print(f"Toplam chunk sayısı: {len(hepsi['ids'])}")

# İçeriklere göre duplicate say
icerik_sayisi = Counter(hepsi['documents'])
duplicateler = {icerik: sayi for icerik, sayi in icerik_sayisi.items() if sayi > 1}

print(f"Duplicate içerik sayısı: {len(duplicateler)}")
print(f"Toplam fazlalık: {sum(s-1 for s in duplicateler.values())}")

# Birkaç örnek göster
for icerik, sayi in list(duplicateler.items())[:3]:
    print(f"\n--- {sayi} kere tekrarlanmış ---")
    print(icerik[:200])