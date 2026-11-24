"""Tamamen bağımsız OCR testi (ocr.py / db.py / arayüz gerekmez).

Kullanım:
  1) Aşağıdaki FOTO_KLASORU satırına klasör yolunu yaz, sonra:   python test.py
     ya da yolu doğrudan ver:                                     python test.py "C:\\...\\fotograflar"
  2) Alt klasörler dahil tüm görseller okunur.

Doğru CAS bilgisi (isteğe bağlı, gerçek başarı oranı için):
  - dosya adının içine yaz:  67-64-1_01.jpg
  - ya da DOGRU_CAS_CSV'ye 'dosya,cas' sütunlu bir CSV yolu ver.

Sonuç: sonuc_ocr.csv (her fotoğraftan sonra yazılır; yarıda kalırsa tekrar
çalıştırınca kaldığı yerden devam eder, baştan başlamak için --sifirla).
İşin bitince test.py ve sonuc_ocr.csv'yi silebilirsin; projeye dokunmaz.

Gerekli paketler: pip install easyocr opencv-python numpy pillow pillow-heif
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

FOTO_KLASORU = r"denemegoruntuleri"      # <-- buraya klasör yolunu yaz
DOGRU_CAS_CSV = ""                 # <-- istersen 'dosya,cas' CSV yolu

import csv
import re
import sys
import time
from collections import Counter

import cv2
import easyocr
import numpy as np
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

UZANTILAR = (".jpg", ".jpeg", ".png", ".heic", ".heif")
CIKTI = "sonuc_ocr.csv"
ALANLAR = ["dosya", "dogru_cas", "okunan_cas", "durum", "sure_sn"]

# ============================================================
# ocr.py'den birebir kopya (okuma mantığı değişmedi)
# ============================================================
CAS_REGEX = re.compile(r'^\d{2,7}-\d{2}-\d$')
CAS_SEARCH_REGEX = re.compile(r'\d{2,7}-\d{2}-\d')


def is_valid_cas(cas_value):
    return bool(cas_value) and bool(CAS_REGEX.match(cas_value.strip()))


def create_reader():
    return easyocr.Reader(['en'], gpu=False)


def _tire_duzelt(metin):
    parcalar = metin.split("-")
    if len(parcalar) == 2 and len(parcalar[1]) > 2:
        return f"{parcalar[0]}-{parcalar[1][:2]}-{parcalar[1][2:]}"
    return metin


def _cas_adayi_ayikla(metin):
    metin_duz = metin.replace(" ", "").replace("l", "1").replace("O", "0")
    eslesen = CAS_SEARCH_REGEX.search(metin_duz)
    if eslesen:
        return eslesen.group()
    eslesen = CAS_SEARCH_REGEX.search(_tire_duzelt(metin_duz))
    if eslesen:
        return eslesen.group()
    return None


def extract_cas_from_image(pil_image, reader):
    try:
        img_array = np.array(pil_image.convert('RGB'))
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        h, w = img_bgr.shape[:2]
        max_boyut = 3500
        olcek = min(5.0, max(1.0, max_boyut / max(h, w)))
        buyutulmus = cv2.resize(img_bgr, None, fx=olcek, fy=olcek, interpolation=cv2.INTER_CUBIC)

        gri = cv2.cvtColor(buyutulmus, cv2.COLOR_BGR2GRAY)
        _, otsu = cv2.threshold(gri, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        otsu_bgr = cv2.cvtColor(otsu, cv2.COLOR_GRAY2BGR)
        keskinlestirme_kerneli = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        keskin = cv2.filter2D(buyutulmus, -1, keskinlestirme_kerneli)

        for yontem_img in (buyutulmus, otsu_bgr, keskin):
            sonuclar = reader.readtext(yontem_img)
            if not sonuclar:
                continue

            bulunan = []

            cas_satirlari_y = []
            for (bbox, metin, guven) in sonuclar:
                metin_upper = metin.upper().replace(" ", "")
                if "CAS" in metin_upper and "EC" not in metin_upper and guven > 0.2:
                    cas_y = (bbox[0][1] + bbox[2][1]) / 2
                    cas_satirlari_y.append(cas_y)
                    aday = _cas_adayi_ayikla(metin)
                    if aday:
                        bulunan.append(aday)

            for cas_y in cas_satirlari_y:
                for (bbox2, metin2, guven2) in sonuclar:
                    if guven2 < 0.2:
                        continue
                    metin2_y = (bbox2[0][1] + bbox2[2][1]) / 2
                    if abs(metin2_y - cas_y) < 80:
                        aday = _cas_adayi_ayikla(metin2)
                        if aday:
                            bulunan.append(aday)

            if not bulunan:
                for (_bbox, metin, guven) in sonuclar:
                    if guven < 0.3:
                        continue
                    aday = _cas_adayi_ayikla(metin)
                    if aday:
                        bulunan.append(aday)

            gecerli_adaylar = [b for b in bulunan if is_valid_cas(b)]
            if gecerli_adaylar:
                return gecerli_adaylar[0]

        return None
    except Exception:
        return None


# ============================================================
# Test düzeneği
# ============================================================
def cas_checksum_gecerli(cas):
    """CAS kontrol basamağı doğrulaması (yanlış okumaları etiketsiz de yakalar)."""
    if not is_valid_cas(cas):
        return False
    rakamlar = cas.replace("-", "")
    toplam = sum(int(r) * i for i, r in enumerate(reversed(rakamlar[:-1]), start=1))
    return toplam % 10 == int(rakamlar[-1])


def gorselleri_bul(klasor):
    bulunanlar = []
    for kok, _, dosyalar in os.walk(klasor):
        for d in dosyalar:
            if d.lower().endswith(UZANTILAR):
                bulunanlar.append(os.path.relpath(os.path.join(kok, d), klasor))
    return sorted(bulunanlar)


def dogru_cas_sozlugu(dosyalar):
    dogru = {}
    if DOGRU_CAS_CSV:
        with open(DOGRU_CAS_CSV, encoding="utf-8-sig", newline="") as f:
            for s in csv.DictReader(f):
                dogru[s["dosya"].strip()] = s["cas"].strip()
    else:
        for d in dosyalar:
            m = CAS_SEARCH_REGEX.search(os.path.basename(d))
            if m:
                dogru[d] = m.group()
    return dogru


def main():
    argumanlar = [a for a in sys.argv[1:] if not a.startswith("--")]
    klasor = argumanlar[0] if argumanlar else FOTO_KLASORU

    if "--sifirla" in sys.argv and os.path.exists(CIKTI):
        os.remove(CIKTI)

    if not os.path.isdir(klasor):
        sys.exit(f"Klasör bulunamadı: {klasor}")
    dosyalar = gorselleri_bul(klasor)
    if not dosyalar:
        sys.exit(f"'{klasor}' içinde görsel bulunamadı.")

    dogru = dogru_cas_sozlugu(dosyalar)
    print(f"{len(dosyalar)} görsel bulundu, {len(dogru)} tanesi için doğru CAS biliniyor.\n")

    sonuclar = {}
    if os.path.exists(CIKTI):
        with open(CIKTI, encoding="utf-8-sig", newline="") as f:
            sonuclar = {s["dosya"]: s for s in csv.DictReader(f)}
        if sonuclar:
            print(f"{len(sonuclar)} görsel önceki çalışmadan alındı, devam ediliyor.\n")

    print("EasyOCR modeli yükleniyor (ilk seferde indirir)...")
    reader = create_reader()

    yeni = not os.path.exists(CIKTI)
    with open(CIKTI, "a", encoding="utf-8-sig", newline="") as f:
        yazar = csv.DictWriter(f, fieldnames=ALANLAR)
        if yeni:
            yazar.writeheader()

        for i, ad in enumerate(dosyalar, 1):
            if ad in sonuclar:
                continue
            t0 = time.time()
            hata = False
            try:
                img = Image.open(os.path.join(klasor, ad))
                img.load()
                okunan = extract_cas_from_image(img, reader)
            except Exception:
                okunan, hata = None, True
            sure = round(time.time() - t0, 1)

            beklenen = dogru.get(ad, "")
            if hata:
                durum = "HATA"
            elif okunan is None:
                durum = "BULUNAMADI"
            elif not beklenen:
                durum = "OKUNDU_(etiket_yok)"
            elif okunan == beklenen:
                durum = "DOGRU"
            else:
                durum = "YANLIS"

            satir = {"dosya": ad, "dogru_cas": beklenen, "okunan_cas": okunan or "",
                     "durum": durum, "sure_sn": sure}
            yazar.writerow(satir)
            f.flush()
            sonuclar[ad] = satir
            print(f"[{i:>3}/{len(dosyalar)}] {ad:<40} okunan={okunan or '-':<14} "
                  f"dogru={beklenen or '?':<14} {durum} ({sure}s)")

    n = len(dosyalar)
    sayac = Counter(sonuclar[d]["durum"] for d in dosyalar if d in sonuclar)
    okunan_sayisi = n - sayac["BULUNAMADI"] - sayac["HATA"]
    checksum_ok = sum(1 for d in dosyalar if sonuclar.get(d, {}).get("okunan_cas")
                      and cas_checksum_gecerli(sonuclar[d]["okunan_cas"]))
    etiketli = sayac["DOGRU"] + sayac["YANLIS"] + sum(
        1 for d in dosyalar if sonuclar.get(d, {}).get("durum") == "BULUNAMADI"
        and sonuclar[d]["dogru_cas"])

    print("\n" + "=" * 60)
    print(f"Toplam görsel              : {n}")
    print(f"CAS okunabilen             : {okunan_sayisi}  (%{100 * okunan_sayisi / n:.1f})")
    print(f"CAS kontrol basamağı geçen : {checksum_ok}  (okunanların %{100 * checksum_ok / max(okunan_sayisi, 1):.1f}'i)")
    print(f"Bulunamadı                 : {sayac['BULUNAMADI']}")
    print(f"Hata                       : {sayac['HATA']}")
    if etiketli:
        print(f"\nDoğru CAS'ı bilinen        : {etiketli}")
        print(f"  Tam doğru                : {sayac['DOGRU']}  (%{100 * sayac['DOGRU'] / etiketli:.1f})  <-- GERÇEK BAŞARI ORANI")
        print(f"  Yanlış okunan            : {sayac['YANLIS']}")
    else:
        print("\n(Doğru CAS bilgisi yok: sadece okunabilirlik oranı verildi, gerçek doğruluk ölçülemedi.)")
    print(f"\nAyrıntılar: {CIKTI}")


if __name__ == "__main__":
    main()