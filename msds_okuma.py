import fitz  # PyMuPDF
import re
import os
from deep_translator import GoogleTranslator
from h_kodlari_sozluk import h_kodu_aciklama_getir
import db

KLASOR_ADI = "kaynak_msds"

cevirmen = GoogleTranslator(source='auto', target='tr')


# ============================================================
# FİZİKSEL HAL ÇEKME (SECTION 9 / BÖLÜM 9)
# ============================================================

FIZIKSEL_HAL_HARITASI = [
    # (ingilizce/türkçe anahtar kelime regex, türkçe karşılık, OLASILIK ALGORİTMASI İÇİN kategori)
    (r"\bgas(es)?\b|\bgaz\b",                     "Gaz",            "gaz"),
    (r"\baerosol\b",                              "Aerosol",        "gaz"),
    (r"\bvapor(s)?\b|\bbuhar\b",                  "Buhar",          "gaz"),
    (r"\bfume(s)?\b|\bduman\b",                   "Duman",          "gaz"),
    (r"\bpowder\b|\btoz\b",                       "Toz",            "tozsivi"),
    (r"\bfine\s+powder\b|\bince\s+toz\b",         "İnce Toz",       "tozsivi"),
    (r"\bdust\b",                                 "Toz",            "tozsivi"),
    (r"\bgranul\w*\b|\bgranül\b",                 "Granül",         "kati"),
    (r"\bpellet(s)?\b|\bpelet\b",                 "Pelet",          "kati"),
    (r"\bsolid\b|\bkat[ıi]\b",                    "Katı",           "kati"),
    (r"\bcrystal\w*\b|\bkristal\b",               "Kristal",        "kati"),
    (r"\bflake(s)?\b|\bpul\b",                    "Pul/Flake",      "kati"),
    (r"\bpaste\b|\bmacun\b",                      "Macun",          "tozsivi"),
    (r"\bgel\b|\bjel\b",                          "Jel",            "tozsivi"),
    (r"\bviscous\s+liquid\b|\bviskoz\s+s[ıi]v[ıi]\b", "Viskoz Sıvı", "sivi"),
    (r"\bliquid\b|\bs[ıi]v[ıi]\b",                "Sıvı",           "sivi"),
]


def section_9_1_blogunu_ayikla(tam_metin):
    # Hem İngilizce SECTION hem de Türkçe BÖLÜM / BOLUM veya 9.1 ibarelerini kapsar
    baslangic_match = re.search(r"(?:SECTION|BÖLÜM|BOLUM)\s*9[:\.\s]|9\.1\.\s+Temel\s+fiziksel", tam_metin, re.IGNORECASE)
    if not baslangic_match:
        return ""

    baslangic = baslangic_match.start()

    # Bölüm 10'a kadar olan kısmı kes
    bitis_match = re.search(r"(?:SECTION|BÖLÜM|BOLUM)\s*10[:\.\s]|10\.1\.", tam_metin[baslangic:], re.IGNORECASE)
    if bitis_match:
        bitis = baslangic + bitis_match.start()
    else:
        bitis = min(baslangic + 2500, len(tam_metin))  # pencereyi biraz daralttık

    return tam_metin[baslangic:bitis]


def fiziksel_hal_coz(tam_metin):
    blok = section_9_1_blogunu_ayikla(tam_metin)
    if not blok:
        return "", ""

    # Türkçe ve İngilizce hal belirten alt başlıkları yakalayan regex
    etiket_pattern = r"(Physical\s+state|Appearance|Form\s*/\s*Appearance|Form\b|Fiziksel\s+Durum(u)?|Fiziksel\s+Hal(i)?|Görünüm|Hal)\s*[:\-]?\s*(.{0,120}?)(?=\n[A-ZÇĞİÖŞÜ][a-zçğıöşü]|$)"

    adaylar = []
    for m in re.finditer(etiket_pattern, blok, re.IGNORECASE | re.DOTALL):
        adaylar.append(m.group(4)) # Asıl değeri (örn: "Katı", "Liquid") alır

    if not adaylar:
        adaylar.append(blok)

    for aday in adaylar:
        if not aday:
            continue
        aday_temiz = aday.strip()
        for regex_pattern, tr_karsilik, kategori in FIZIKSEL_HAL_HARITASI:
            if re.search(regex_pattern, aday_temiz, re.IGNORECASE):
                return tr_karsilik, kategori

    return "", ""


# ============================================================
# OLASILIK (O) PUANI - Fiziksel Hal Algoritması
# ============================================================

OLASILIK_PUANLARI = {
    "gaz":      10,   # Gaz veya Çok Uçucu Sıvı
    "tozsivi":  6,    # Uçucu Sıvı / İnce Toz (toz, gel, macun bu gruba eşlendi)
    "sivi":     3,    # Sıvı (Uçucu olmayan)
    "kati":     1,    # Katı / Granül
}


def olasilik_puani_hesapla(kategori):
    return OLASILIK_PUANLARI.get(kategori, "")


# ============================================================
# ŞİDDET (Ş) PUANI - H Kodu Eşleştirme Tablosu
# ============================================================

H_SIDDET_GRUPLARI = [
    ({"H200", "H201", "H224", "H330"}, 100),
    ({"H300", "H301", "H310", "H340", "H350"}, 40),
    ({"H314", "H318", "H370", "H372"}, 15),
    ({"H302", "H312", "H332", "H317"}, 7),
    ({"H315", "H319", "H335", "H336"}, 3),
    ({"H402", "H412"}, 1),
]


def siddet_puani_hesapla(h_ifadeleri):
    if not h_ifadeleri:
        return ""

    en_yuksek_puan = None
    for h in h_ifadeleri:
        kod = h.get("kod", "").strip().upper()
        alt_kodlar = re.findall(r"H\d{3}", kod)
        if not alt_kodlar:
            continue
        for alt_kod in alt_kodlar:
            for grup, puan in H_SIDDET_GRUPLARI:
                if alt_kod in grup:
                    if en_yuksek_puan is None or puan > en_yuksek_puan:
                        en_yuksek_puan = puan

    return en_yuksek_puan if en_yuksek_puan is not None else ""


# ============================================================
# PDF ANALİZ (CAS, İSİM, H/P KODLARI, FİZİKSEL HAL)
# ============================================================

def msds_analiz_ve_cevir(pdf_yolu):
    dosya_adi = os.path.basename(pdf_yolu)
    doc = fitz.open(pdf_yolu)
    tam_metin = ""
    for sayfa in doc:
        tam_metin += sayfa.get_text()
    doc.close()

    temiz_metin = " ".join(tam_metin.split())

    cas_match = re.search(r"CAS[^\d]{0,30}?(\d{2,7}-\d{2}-\d)", temiz_metin, re.IGNORECASE)
    cas_no = cas_match.group(1) if cas_match else "Bulunamadı"

    if cas_no == "Bulunamadı":
        return None

    # BÖLÜM 1 içerisindeki ürün adını çeken geliştirilmiş (Türkçe/İngilizce) regex
    ad_match = re.search(
        r"(?:Ürün adı|Madde/Müstahzar adı|Kimyasal Adı|Product name|Madde/Karışım kimliği)[\s:]+([A-Za-z0-9\-\s\(\)\[\]\.,çğıöşüÇĞİÖŞÜ]{3,70}?)(?=\s*(?:Ürün kodu|Ürün Kodu|EC numarası|CAS Numarası|CAS|REACH|Product|1\.\d|2\.\d|Eş anlamlı|Firma|Tedarikçi|Kullanım))",
        temiz_metin, re.IGNORECASE
    )
    
    if ad_match:
        kimyasal_adi = ad_match.group(1).strip()
        ad_kaynagi = "pdf_icerigi"
    else:
        kimyasal_adi = dosya_adi.replace(".pdf", "")
        ad_kaynagi = "dosya_adi_yedek"

    h_kod_pattern = r"\bH\d{3}(?:[A-Za-z]{0,2})?(?:\s*\+\s*H?\d{3}(?:[A-Za-z]{0,2})?)*\b"
    ham_h_kodlari = re.findall(h_kod_pattern, tam_metin)

    h_kod_seti = set()
    for kod in ham_h_kodlari:
        kod_norm = re.sub(r"\s*\+\s*", "+", kod.strip())
        h_kod_seti.add(kod_norm)

    h_listesi = []
    eslesmeyen_h_kodlari = []
    for kod in sorted(h_kod_seti):
        aciklama = h_kodu_aciklama_getir(kod)
        if aciklama is None:
            eslesmeyen_h_kodlari.append(kod)
            continue
        h_listesi.append({"kod": kod, "aciklama": aciklama})

    p_bulunanlar = re.findall(r"(P\d{3}(?:\+P?\d{3})*)\s+([^\n\"]+)", tam_metin)
    p_listesi = [{"kod": k.strip().replace("$", ""), "aciklama": a.strip()} for k, a in p_bulunanlar]
    p_listesi = [dict(t) for t in {tuple(d.items()) for d in p_listesi}]

    fiziksel_hal_tr, hal_kategori = fiziksel_hal_coz(tam_metin)
    olasilik_puani = olasilik_puani_hesapla(hal_kategori)

    print(f"   🔄 {cas_no} için P kodları Türkçeye çevriliyor...")
    for p in p_listesi:
        try:
            p['aciklama'] = cevirmen.translate(p['aciklama'])
        except Exception:
            pass

    siddet_puani = siddet_puani_hesapla(h_listesi)

    return {
        "kimyasal_adi": kimyasal_adi,
        "ad_kaynagi": ad_kaynagi,
        "cas_no": cas_no,
        "h_ifadeleri": sorted(h_listesi, key=lambda x: x["kod"]),
        "p_ifadeleri": sorted(p_listesi, key=lambda x: x["kod"]),
        "fiziksel_hal": fiziksel_hal_tr,
        "olasilik_puani": olasilik_puani,
        "siddet_puani": siddet_puani,
        "dosya_kaynagi": dosya_adi,
        "_eslesmeyen_h_kodlari": eslesmeyen_h_kodlari,
    }


if __name__ == "__main__":
    koleksiyon = db.get_collection()
    if koleksiyon is None:
        print("❌ HATA: MongoDB Atlas'a bağlanılamadı. İnternet/URI'yi kontrol et.")
        exit()

    # DİKKAT: Veritabanını sıfırlamak (tamamen silmek) istersen aşağıdaki satırların başındaki '#' işaretini kaldır.
    # print("🧹 Eski veriler temizleniyor...")
    # koleksiyon.delete_many({}) 
    # print("✨ Veritabanı sıfırlandı!")
    
    if not os.path.exists(KLASOR_ADI):
        os.makedirs(KLASOR_ADI)

    dosyalar = [f for f in os.listdir(KLASOR_ADI) if f.lower().endswith(".pdf")]

    if not dosyalar:
        print(f"⚠️ '{KLASOR_ADI}' klasöründe PDF bulunamadı.")
    else:
        print(f"🚀 Toplam {len(dosyalar)} MSDS taranıyor ve işleniyor...\n")

        ad_kaynagi_yedek_olanlar = []
        tum_eslesmeyen_h_kodlari = set()

        for dosya in dosyalar:
            
            # --- Zaten Eklenmiş Dosyaları Atla (Kaldığı Yerden Devam Etme) ---
            mevcut_kayit = koleksiyon.find_one({"dosya_kaynagi": dosya})
            if mevcut_kayit:
                print(f"⏩ '{dosya}' zaten veritabanında var, atlanıyor...")
                continue
            # ------------------------------------------------------------------

            tam_yol = os.path.join(KLASOR_ADI, dosya)
            veri = msds_analiz_ve_cevir(tam_yol)

            if veri:
                eslesmeyenler = veri.pop("_eslesmeyen_h_kodlari", [])
                tum_eslesmeyen_h_kodlari.update(eslesmeyenler)

                koleksiyon.update_one({"cas_no": veri["cas_no"]}, {"$set": veri}, upsert=True)
                print(f"✅ Veritabanına Eklendi: {veri['kimyasal_adi']} "
                      f"(CAS: {veri['cas_no']}, Hal: {veri['fiziksel_hal'] or '—'}, "
                      f"Olasılık: {veri['olasilik_puani'] or '—'}, "
                      f"Şiddet: {veri['siddet_puani'] or '—'}, "
                      f"H Kodu Sayısı: {len(veri['h_ifadeleri'])})")
                
                if veri["ad_kaynagi"] == "dosya_adi_yedek":
                    ad_kaynagi_yedek_olanlar.append(dosya)

        print("\n🎉 İşlem tamamlandı! Veritabanı güncel.")
        
        if ad_kaynagi_yedek_olanlar:
            print(f"\n⚠️  {len(ad_kaynagi_yedek_olanlar)} dosyada kimyasal adı PDF içeriğinden "
                  f"çekilemedi, dosya adı kullanıldı. Bu kayıtları elle kontrol etmeni öneririm:")
            for d in ad_kaynagi_yedek_olanlar:
                print(f"   - {d}")

        if tum_eslesmeyen_h_kodlari:
            print(f"\n⚠️  Sözlükte karşılığı bulunamayan {len(tum_eslesmeyen_h_kodlari)} kod tespit edildi "
                  f"(muhtemelen yanlış yakalama veya sözlükte eksik varyant). Veritabanına YAZILMADI:")
            for kod in sorted(tum_eslesmeyen_h_kodlari):
                print(f"   - {kod}")
            print("   Bunlar gerçek H kodlarıysa h_kodlari_sozluk.py'ye ekleyebiliriz.")