import os
# Anaconda + EasyOCR/PyTorch kullanan bilgisayarlarda görülen "OMP: Error #15"
# çökmesini önler. Diğer tüm import'lardan ÖNCE gelmelidir.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import streamlit as st
from PIL import Image
import pandas as pd
from pillow_heif import register_heif_opener
import io
import time
import uuid
import hashlib
import math

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.formatting.rule import FormulaRule
from openpyxl.worksheet.datavalidation import DataValidation

import db
import ocr
import risk_hesap

# HEIC/HEIF (iPhone) formatını PIL'in okuyabilmesi için kaydediyoruz
register_heif_opener()

# ==============================================================================
# 1. SAYFA YAPILANDIRMASI & LÜKS TEMATİK CSS (UI/UX)
# ==============================================================================
st.set_page_config(
    page_title="Akıllı İSG Karar Destek ve Risk Analiz Sistemi",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Adaptive Theme CSS (hem açık hem koyu temada çalışır)
st.markdown("""
<style>
    .stApp {
        background-image:
            radial-gradient(circle at 10% 10%, rgba(99, 102, 241, 0.05) 0%, transparent 40%),
            radial-gradient(circle at 90% 90%, rgba(6, 182, 212, 0.04) 0%, transparent 40%);
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Executive Header */
    .executive-header {
        background: var(--secondary-background-color);
        border: 1px solid rgba(99, 102, 241, 0.25);
        backdrop-filter: blur(16px);
        padding: 1.25rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .header-title-text {
        font-size: 1.45rem;
        font-weight: 800;
        color: var(--text-color);
        margin: 0;
    }
    .header-subtitle-text {
        font-size: 0.82rem;
        color: var(--text-color);
        opacity: 0.55;
        margin-top: 0.2rem;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: var(--secondary-background-color);
        padding: 6px;
        border-radius: 12px;
        border: 1px solid rgba(99, 102, 241, 0.2);
    }
    .stTabs [data-baseweb="tab"] {
        height: 46px;
        border-radius: 8px;
        color: var(--text-color);
        font-weight: 600;
        font-size: 0.88rem;
        background-color: transparent;
        border: none;
        opacity: 0.65;
    }
    .stTabs [aria-selected="true"] {
        background-color: #6366f1 !important;
        color: #ffffff !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
        opacity: 1 !important;
    }

    /* Scanner Viewfinder Box */
    .scanner-viewfinder-box {
        border: 2px dashed #06b6d4;
        border-radius: 14px;
        background: rgba(6, 182, 212, 0.05);
        padding: 0.85rem;
        text-align: center;
        margin-bottom: 1rem;
    }
    .scanner-guide-label {
        color: #06b6d4;
        font-weight: 700;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    /* Results Editor Container */
    .editor-container-box {
        background: var(--secondary-background-color);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 16px;
        padding: 1.5rem;
        margin-top: 1.5rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    }

    /* CAS Rapor Kartı */
    .cas-report-card {
        background: var(--secondary-background-color);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 16px;
        padding: 1.25rem 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    }
    .cas-report-title {
        font-size: 1.2rem;
        font-weight: 800;
        color: var(--text-color);
        margin: 0;
    }
    .cas-report-sub {
        font-size: 0.82rem;
        color: var(--text-color);
        opacity: 0.55;
        margin-top: 0.25rem;
    }
    .cas-risk-badge {
        display: inline-block;
        margin-top: 0.75rem;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
        background: rgba(99, 102, 241, 0.15);
        border: 1px solid rgba(99, 102, 241, 0.45);
        color: #6366f1;
    }

    /* Havuzdaki manuel CAS girişi kartı (fotoğraf yerine) */
    .manual-cas-card {
        height: 170px;
        border: 2px dashed #6366f1;
        border-radius: 12px;
        background: rgba(99, 102, 241, 0.05);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.35rem;
        margin-bottom: 0.5rem;
    }
    .manual-cas-card .ikon { font-size: 2.2rem; }
    .manual-cas-card .cas { font-family: monospace; font-weight: 800; font-size: 1.05rem; color: #6366f1; }
    .manual-cas-card .etiket { font-size: 0.75rem; color: var(--text-color); opacity: 0.5; text-transform: uppercase; letter-spacing: 0.04em; }

    /* Sekme görünümlü seçim çubuğu */
    div[role="radiogroup"] {
        gap: 8px;
        background-color: var(--secondary-background-color);
        padding: 6px;
        border-radius: 12px;
        border: 1px solid rgba(99, 102, 241, 0.2);
    }
    div[role="radiogroup"] > label {
        padding: 0.55rem 1rem;
        border-radius: 8px;
        margin: 0;
    }
    div[role="radiogroup"] > label:has(input:checked) {
        background-color: #6366f1;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. ÖNBELLEKLİ KAYNAKLAR (MongoDB bağlantısı & EasyOCR modeli)
# ==============================================================================
@st.cache_resource
def _cached_mongo_collection():
    coll = db.get_collection()
    if coll is None:
        # Başarısız bağlantıyı önbelleğe alma; bir sonraki denemede tekrar bağlanılsın
        raise ConnectionError(db.last_error or "MongoDB bağlantısı kurulamadı")
    return coll

def get_mongo_collection():
    """MongoDB Atlas bağlantısını Streamlit oturumu boyunca önbellekte tutar.
    Sadece BAŞARILI bağlantı önbelleğe alınır; hata olursa None döner."""
    try:
        return _cached_mongo_collection()
    except ConnectionError:
        return None

@st.cache_resource
def get_ocr_reader():
    """EasyOCR modelini bir kez yükleyip önbellekte tutar (ağır/yavaş bir işlem)."""
    return ocr.create_reader()

# ==============================================================================
# 2b. ORTAK ANALİZ FONKSİYONU (Toplu analiz + CAS'tan Rapor sekmesi kullanır)
# ==============================================================================
def cas_analiz_et(target_cas, collection, F):
    """
    Tek bir CAS numarası için MongoDB'den MSDS kaydını çeker ve Fine Kinney
    hesabını yapar. (sonuc_sozlugu, mongo_dokumani) döndürür.
    Kayıt bulunamazsa mongo_dokumani None olur ve değerler 'Hesaplanamadı' işaretlenir.
    """
    cas_valid = ocr.is_valid_cas(target_cas)

    db_doc = None
    if cas_valid and collection is not None:
        try:
            # MongoDB Atlas sorgusu: {"cas_no": target_cas}
            db_doc = collection.find_one({"cas_no": target_cas})
        except Exception:
            db_doc = None

    if db_doc:
        chem_name = db_doc.get("kimyasal_adi", "Bilinmeyen Kimyasal")
        h_raw = db_doc.get("h_ifadeleri", [])

        # H ifadelerini birleştir
        if isinstance(h_raw, list):
            h_codes_list = [h.get("kod", "") if isinstance(h, dict) else str(h) for h in h_raw]
            h_codes_str = ", ".join([c for c in h_codes_list if c])
        else:
            h_codes_list = [str(h_raw)]
            h_codes_str = str(h_raw)

        if not h_codes_str:
            h_codes_str = "H000 (Bilinmiyor)"

        # Olasılık O: Güvenli Tarafta Kalma İlkesi (Varsayılan 6.0, güvenli dönüşüm)
        olasilik = risk_hesap.safe_float(db_doc.get("olasilik_puani"), default=6.0)

        # Şiddet S: En Kötü Senaryo MAX kuralı veya DB değeri (güvenli dönüşüm)
        if db_doc.get("siddet_puani"):
            siddet = risk_hesap.safe_float(db_doc["siddet_puani"], default=float(risk_hesap.calculate_max_severity(h_codes_list)))
        else:
            siddet = float(risk_hesap.calculate_max_severity(h_codes_list))

        score = olasilik * siddet * F
        deg = risk_hesap.risk_level_calculator(score)
        display_cas = target_cas
    else:
        # CAS geçersiz/eşleşmedi: KESİNLİKLE rastgele veri üretilmez, durum net olarak işaretlenir
        chem_name = "Veritabanında Bulunamadı"
        h_codes_str = "Bulunamadı"
        olasilik = "Hesaplanamadı"
        siddet = "Hesaplanamadı"
        score = "Hesaplanamadı"
        deg = "Hesaplanamadı"
        display_cas = target_cas if target_cas else "Tespit Edilemedi / Geçersiz Format"

    sonuc = {
        "CAS Numarası": display_cas,
        "Kimyasal Adı": chem_name,
        "H Tehlike Kodları": h_codes_str,
        "Olasılık (O)": olasilik,
        "Şiddet (S)": siddet,
        "Frekans (F)": F,
        "Fine Kinney Skoru": score,
        "Risk Derecesi": deg
    }
    return sonuc, db_doc

# ==============================================================================
# 2c. FINE KINNEY RİSK ANALİZİ TABLOSU (EXCEL ÇIKTISI)
#     Tehlikeler = H kodları, Alınacak Tedbirler = P kodları.
#     Risk Skoru / Derecesi / Önem Sırası Excel formülüyle hesaplanır.
# ==============================================================================
# Sütun düzeni (resmi Fine Kinney tablosu ile aynı sıra)
SUTUNLAR = [
    # (harf, başlık, genişlik, dikey_yazı)
    ("A", "No", 5, False),
    ("B", "Tehlike yeri\nBölüm/Birim", 18, False),
    ("C", "Tehlike Tanımı", 30, False),
    ("D", "Risk Tanımı\n(Tehlike İfadeleri - H Kodları)", 45, False),
    ("E", "Olasılık", 6, True),
    ("F", "Şiddet", 6, True),
    ("G", "Frekans", 6, True),
    ("H", "Risk Skoru", 7, True),
    ("I", "Risk Derecesi", 16, False),
    ("J", "Aksiyon (Alınacak Tedbirler)\n(Önlem İfadeleri - P Kodları)", 55, False),
    # K-O: Kontrol Tedbirleri Sonrası Risk Verileri
    ("K", "Olasılık", 5, True),
    ("L", "Şiddet", 5, True),
    ("M", "Frekans", 5, True),
    ("N", "Risk Skoru", 6, True),
    ("O", "Risk Derecesi", 16, False),
    ("P", "Sorumlu Kişi", 16, False),
    ("Q", "Tedbir\nPlanlama\nTarihi", 11, False),
    ("R", "Tedbir\nAlma\nTarihi", 11, False),
    ("S", "Risk\nÖnem\nsırası", 8, False),
]
SON_SUTUN = "S"

# Fine Kinney standart değer listeleri (açılır listeler için)
OLASILIK_DEGERLERI = "0.2,0.5,1,3,6,10"
SIDDET_DEGERLERI = "1,3,7,15,40,100"
FREKANS_DEGERLERI = "0.5,1,2,3,6,10"

# Stiller
FONT = "Calibri"
ince = Side(style="thin", color="000000")
kalin = Side(style="medium", color="000000")
KENAR = Border(left=ince, right=ince, top=ince, bottom=ince)
BASLIK_DOLGU = PatternFill("solid", start_color="D9D9D9")
GIRDI_DOLGU = PatternFill("solid", start_color="FCD5B4")   # O/Ş/F (şeftali)
SKOR_DOLGU = PatternFill("solid", start_color="00B050")    # Risk skoru (yeşil)

# Risk derecesine göre renk (risk_hesap.risk_level_calculator eşikleriyle aynı)
RISK_RENKLERI = [
    ("<20", "00B050"),    # Kabul Edilebilir
    ("<70", "FFFF00"),    # Dikkate Değer
    ("<200", "FFC000"),   # Önemli
    ("<400", "FF0000"),   # Yüksek
    (">=400", "C00000"),  # Çok Yüksek
]


def _risk_derecesi_formulu(skor_hucresi):
    """risk_hesap.risk_level_calculator ile aynı eşik ve etiketler."""
    s = skor_hucresi
    return (
        f'=IF({s}="","",IF({s}<20,"Kabul Edilebilir Risk",'
        f'IF({s}<70,"Dikkate Değer Risk",IF({s}<200,"Önemli Risk",'
        f'IF({s}<400,"Yüksek Risk","Çok Yüksek Risk (Acil Eylem)")))))'
    )


def _sayi(deger):
    """Sayıya çevrilebiliyorsa float, değilse None ('Hesaplanamadı' vb.)."""
    try:
        if deger is None or (isinstance(deger, str) and not deger.strip()):
            return None
        sonuc = float(deger)
        return None if math.isnan(sonuc) else sonuc
    except (TypeError, ValueError):
        return None


def ifade_metni(liste, bos_mesaj):
    """[{'kod':..., 'aciklama':...}] listesini hücreye yazılacak alt alta metne çevirir."""
    satirlar = []
    for x in (liste or []):
        if isinstance(x, dict):
            kod = str(x.get("kod", "")).strip()
            aciklama = str(x.get("aciklama", "")).strip()
            satirlar.append(f"{kod}: {aciklama}" if aciklama else kod)
        elif x:
            satirlar.append(str(x))
    return "\n".join(satirlar) if satirlar else bos_mesaj


def tehlike_tanimi(kimyasal_adi, cas_no, fiziksel_hal=None):
    metin = f"{kimyasal_adi}\n(CAS: {cas_no})"
    if fiziksel_hal:
        metin += f"\nFiziksel hal: {fiziksel_hal}"
    return metin


def _satir_yuksekligi(degerler):
    """Hücre metinlerinin sığacağı yaklaşık satır yüksekliği."""
    en_cok = 2
    genislikler = {harf: gen for harf, _, gen, _ in SUTUNLAR}
    for harf, metin in degerler.items():
        if not metin:
            continue
        karakter_sigasi = max(1, int(genislikler[harf] * 1.1))
        satir = sum(max(1, math.ceil(len(p) / karakter_sigasi)) for p in str(metin).split("\n"))
        en_cok = max(en_cok, satir)
    return min(409, 15 * en_cok + 4)


def _siralama_anahtari(veri):
    """Risk skoru (O x Ş x F) yüksek olan önce; skoru olmayanlar en sonda."""
    o, s, f = _sayi(veri.get("olasilik")), _sayi(veri.get("siddet")), _sayi(veri.get("frekans"))
    if None in (o, s, f):
        return (1, 0)
    return (0, -(o * s * f))


def fine_kinney_excel(satirlar, bos_satir_sayisi=0):
    """
    satirlar: her biri şu anahtarları içeren sözlük listesi:
        bolum, tehlike, risk, aksiyon, olasilik, siddet, frekans
    Dönüş: .xlsx dosyasının byte içeriği.
    Satırlar risk skoruna göre EN YÜKSEKTEN EN DÜŞÜĞE sıralanır;
    skoru hesaplanamayan satırlar en sona konur.
    """
    satirlar = sorted(satirlar, key=_siralama_anahtari)

    wb = Workbook()
    ws = wb.active
    ws.title = "Fine Kinney Risk Analizi"
    ws.sheet_view.showGridLines = False

    # --- Sütun genişlikleri
    for harf, _, genislik, _ in SUTUNLAR:
        ws.column_dimensions[harf].width = genislik

    # --- Başlık (1-2. satırlar)
    ws.merge_cells(f"A1:{SON_SUTUN}2")
    ws["A1"] = "FINE KINNEY RİSK ANALİZİ TABLOSU"
    ws["A1"].font = Font(name=FONT, size=20)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="bottom")
    ws.row_dimensions[1].height = 18
    ws.row_dimensions[2].height = 30

    # --- Sütun başlıkları (3-4. satırlar)
    baslik_font = Font(name=FONT, size=10, bold=True)
    for harf, baslik, _, dikey in SUTUNLAR:
        if harf in "KLMNO":
            hucre = ws[f"{harf}4"]
        else:
            ws.merge_cells(f"{harf}3:{harf}4")
            hucre = ws[f"{harf}3"]
        hucre.value = baslik
        hucre.font = baslik_font
        hucre.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True,
            text_rotation=90 if dikey else 0
        )

    ws.merge_cells("K3:O3")
    ws["K3"] = "Kontrol Tedbirleri Sonrası Risk Verileri"
    ws["K3"].font = baslik_font
    ws["K3"].alignment = Alignment(horizontal="center", vertical="center")

    for satir in (3, 4):
        for harf, *_ in SUTUNLAR:
            ws[f"{harf}{satir}"].fill = BASLIK_DOLGU
            ws[f"{harf}{satir}"].border = KENAR
    ws.row_dimensions[3].height = 20
    ws.row_dimensions[4].height = 62

    # --- Veri satırları
    ilk = 5
    toplam = len(satirlar) + bos_satir_sayisi
    son = ilk + toplam - 1
    veri_font = Font(name=FONT, size=10)
    ust_sol = Alignment(horizontal="left", vertical="top", wrap_text=True)
    orta = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for i in range(toplam):
        r = ilk + i
        veri = satirlar[i] if i < len(satirlar) else {}

        ws[f"A{r}"] = i + 1
        ws[f"B{r}"] = veri.get("bolum")
        ws[f"C{r}"] = veri.get("tehlike")
        ws[f"D{r}"] = veri.get("risk")
        ws[f"E{r}"] = _sayi(veri.get("olasilik"))
        ws[f"F{r}"] = _sayi(veri.get("siddet"))
        ws[f"G{r}"] = _sayi(veri.get("frekans"))
        ws[f"H{r}"] = f'=IF(COUNT(E{r}:G{r})=3,E{r}*F{r}*G{r},"")'
        ws[f"I{r}"] = _risk_derecesi_formulu(f"H{r}")
        ws[f"J{r}"] = veri.get("aksiyon")
        ws[f"N{r}"] = f'=IF(COUNT(K{r}:M{r})=3,K{r}*L{r}*M{r},"")'
        ws[f"O{r}"] = _risk_derecesi_formulu(f"N{r}")
        ws[f"S{r}"] = f'=IF(H{r}="","",RANK(H{r},$H${ilk}:$H${son}))'

        for harf, *_ in SUTUNLAR:
            hucre = ws[f"{harf}{r}"]
            hucre.font = veri_font
            hucre.border = KENAR
            hucre.alignment = ust_sol if harf in "BCDJP" else orta
        for harf in "EFGKLM":
            ws[f"{harf}{r}"].fill = GIRDI_DOLGU
        for harf in "HN":
            ws[f"{harf}{r}"].fill = SKOR_DOLGU
            ws[f"{harf}{r}"].font = Font(name=FONT, size=11, bold=True)
        for harf in "QR":
            ws[f"{harf}{r}"].number_format = "DD.MM.YYYY"

        ws.row_dimensions[r].height = _satir_yuksekligi(
            {h: veri.get(k) for h, k in (("B", "bolum"), ("C", "tehlike"), ("D", "risk"), ("J", "aksiyon"))}
        ) if veri else 30

    # --- Açılır listeler (O / Ş / F)
    for liste, sutunlar in ((OLASILIK_DEGERLERI, "EK"), (SIDDET_DEGERLERI, "FL"), (FREKANS_DEGERLERI, "GM")):
        dv = DataValidation(type="list", formula1=f'"{liste}"', allow_blank=True)
        dv.error = "Lütfen listeden bir Fine Kinney değeri seçin."
        dv.errorTitle = "Geçersiz değer"
        ws.add_data_validation(dv)
        for harf in sutunlar:
            dv.add(f"{harf}{ilk}:{harf}{son}")

    # --- Risk derecesine göre renklendirme (skor ve derece hücreleri)
    for skor, derece in (("H", "I"), ("N", "O")):
        for kosul, renk in RISK_RENKLERI:
            yazi_rengi = "FFFFFF" if renk in ("FF0000", "C00000") else "000000"
            kural = FormulaRule(
                formula=[f'AND(ISNUMBER(${skor}{ilk}),${skor}{ilk}{kosul})'],
                fill=PatternFill("solid", start_color=renk, end_color=renk),
                font=Font(color=yazi_rengi, bold=True),
                stopIfTrue=True,
            )
            ws.conditional_formatting.add(f"{skor}{ilk}:{derece}{son}", kural)

    # --- Kalın dış çerçeve (başlık bloğu)
    for harf, *_ in SUTUNLAR:
        ws[f"{harf}3"].border = Border(left=ince, right=ince, top=kalin, bottom=ince)
        ws[f"{harf}4"].border = Border(left=ince, right=ince, top=ince, bottom=kalin)

    # --- Görünüm ve yazdırma ayarları
    ws.freeze_panes = f"B{ilk}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = "3:4"

    tampon = io.BytesIO()
    wb.save(tampon)
    return tampon.getvalue()

def cas_excel_satiri(sonuc, db_doc, lab):
    """CAS analiz sonucunu Fine Kinney Excel tablosunun bir satırına çevirir."""
    return {
        "bolum": lab.split(" (")[0],
        "tehlike": tehlike_tanimi(sonuc["Kimyasal Adı"], sonuc["CAS Numarası"], db_doc.get("fiziksel_hal")),
        "risk": ifade_metni(db_doc.get("h_ifadeleri"), "Sınıflandırılmış tehlike (H) ifadesi yok"),
        "aksiyon": ifade_metni(db_doc.get("p_ifadeleri"), "MSDS'te kayıtlı önlem (P) ifadesi yok"),
        "olasilik": sonuc["Olasılık (O)"],
        "siddet": sonuc["Şiddet (S)"],
        "frekans": sonuc["Frekans (F)"],
    }

# ==============================================================================
# 3. SESSION STATE (STATE MİMARİSİ)
# ==============================================================================
if "photo_pool" not in st.session_state:
    st.session_state.photo_pool = []

if "seen_hashes" not in st.session_state:
    st.session_state.seen_hashes = set()

if "analysis_df" not in st.session_state:
    st.session_state.analysis_df = None

if "cas_report" not in st.session_state:
    st.session_state.cas_report = None

# Toplu analizde bulunan MSDS kayıtları (Excel'e H/P açıklamalarını yazmak için)
if "msds_cache" not in st.session_state:
    st.session_state.msds_cache = {}

# Rapor indirme öncesi çevre bilinçlendirme ekranını kontrol etmek için
if "show_report_warning" not in st.session_state:
    st.session_state.show_report_warning = False
# ==============================================================================
# 4. HEADER (ÜST BİLGİ ALANI VE MONGODB BAĞLANTI DURUMU)
# ==============================================================================
mongo_collection = get_mongo_collection()
db_status_color = "#34d399" if mongo_collection is not None else "#fbbf24"
db_status_text = "● MongoDB Atlas Bağlandı" if mongo_collection is not None else "● MongoDB Çevrimdışı (Lokal Mod)"
if mongo_collection is None and db.last_error:
    with st.expander("⚠️ MongoDB bağlantı hatası detayı"):
        st.code(db.last_error)
        if st.button("🔄 Tekrar Bağlan"):
            st.rerun()

st.markdown(f"""
<div class="executive-header">
    <div>
        <h1 class="header-title-text">🛡️ Akıllı İSG Karar Destek ve Risk Analiz Sistemi</h1>
        <p class="header-subtitle-text">Laboratuvar Kimyasal Şişeleri Görsel Okuma, MongoDB MSDS Sorgulama & Fine Kinney Risk Matrisi</p>
    </div>
    <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); color: {db_status_color}; padding: 0.45rem 1.1rem; border-radius: 20px; font-weight: 700; font-size: 0.85rem;">
        {db_status_text}
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# 5. SOL PANEL (LABORATUVAR SEÇİMİ VE HAVUZ YÖNETİMİ)
# ==============================================================================
with st.sidebar:
    st.markdown("### ⚙️ Kontrol & Ayarlar")

    # Laboratuvar Türü Seçimi (Frekans F)
    lab_choice = st.selectbox(
        "🏛️ Laboratuvar Türü (Frekans - F):",
        options=[
            "Depo (Seyrek Kullanım - F: 1)",
            "Ar-Ge Laboratuvarı (Haftalık Kullanım - F: 3)",
            "Öğrenci Laboratuvarı (Günlük Kullanım - F: 6)",
            "Üretim / Kalite Kontrol (Sürekli Kullanım - F: 10)"
        ],
        index=1
    )
    freq_map = {
        "Depo (Seyrek Kullanım - F: 1)": 1.0,
        "Ar-Ge Laboratuvarı (Haftalık Kullanım - F: 3)": 3.0,
        "Öğrenci Laboratuvarı (Günlük Kullanım - F: 6)": 6.0,
        "Üretim / Kalite Kontrol (Sürekli Kullanım - F: 10)": 10.0
    }
    selected_F = freq_map[lab_choice]

    st.markdown("---")

    # Kümülatif Havuz Sayacı
    pool_count = len(st.session_state.photo_pool)

    st.markdown(f"""
    <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255, 255, 255, 0.08); padding: 0.75rem 1rem; border-radius: 12px; margin-bottom: 0.8rem; display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 0.85rem; font-weight: 600; color: #94a3b8;">Havuzdaki Toplam Kimyasal</span>
        <span style="font-size: 0.95rem; font-weight: 800; color: #06b6d4; background: rgba(6, 182, 212, 0.12); padding: 0.25rem 0.65rem; border-radius: 8px; border: 1px solid rgba(6, 182, 212, 0.3); font-family: monospace;">{pool_count} Adet</span>
    </div>
    """, unsafe_allow_html=True)

    if pool_count > 0:
        if st.button("🧹 Tüm Havuzu Temizle", use_container_width=True):
            st.session_state.photo_pool = []
            st.session_state.seen_hashes = set()
            st.session_state.analysis_df = None
            st.rerun()

# ==============================================================================
# 6. ANA EKRAN (SEKMELİ YÜKLEME & HASH KORUMALI KAMERA ÇEKİMİ & CAS'TAN RAPOR)
# ==============================================================================
# Not: st.tabs butona basılınca ilk sekmeye döndüğü için, seçimi hafızada
# tutan yatay bir st.radio kullanıyoruz (CSS ile sekme gibi görünür).
SEKMELER = [
    "📁 Dosyadan Yükle (Çoklu)",
    "📸 Sınırsız Canlı Kamera Taraması",
    "🧪 CAS Numarasından Rapor"
]
aktif_sekme = st.radio(
    "Yöntem seçin:",
    SEKMELER,
    horizontal=True,
    key="aktif_sekme",
    label_visibility="collapsed"
)

if not ocr.OCR_AVAILABLE:
    st.warning("📷 Fotoğraftan otomatik CAS okuma bu sürümde kapalı (sadece yerel sürümde çalışır). CAS numarasını elle girebilirsiniz.")

# --- TAB 1: ÇOKLU DOSYA YÜKLEME ---
if aktif_sekme == SEKMELER[0]:
    uploaded_files = st.file_uploader(
        "Birden fazla şişe/etiket fotoğrafı seçin:",
        type=["jpg", "png", "jpeg", "heic"],
        accept_multiple_files=True,
        key="file_uploader_widget"
    )

    if uploaded_files:
        added_any = False
        for f in uploaded_files:
            file_bytes = f.getvalue()
            file_hash = hashlib.md5(file_bytes).hexdigest()

            if file_hash not in st.session_state.seen_hashes:
                try:
                    img = Image.open(f)
                    img.load()
                except Exception as e:
                    st.error(f"❌ '{f.name}' açılamadı (bozuk dosya veya desteklenmeyen format): {e}")
                    continue

                with st.spinner(f"🔎 '{f.name}' üzerinde OCR ile CAS numarası aranıyor..."):
                    extracted_cas = ocr.extract_cas_from_image(img, get_ocr_reader())

                st.session_state.photo_pool.append({
                    "id": str(uuid.uuid4()),
                    "hash": file_hash,
                    "name": f.name,
                    "image": img,
                    "source": "Dosya",
                    "extracted_cas": extracted_cas
                })
                st.session_state.seen_hashes.add(file_hash)
                added_any = True

        if added_any:
            st.session_state.analysis_df = None

# --- TAB 2: SINIRSIZ CANLI KAMERA ÇEKİMİ & KILAVUZ ÇERÇEVE ---
if aktif_sekme == SEKMELER[1]:
    st.markdown("""
    <div class="scanner-viewfinder-box">
        <div class="scanner-guide-label">
            🎯 CAS Numarasını Ekran Ortasındaki Kılavuz Çerçeveye Hizalayın
        </div>
    </div>
    """, unsafe_allow_html=True)

    cam_snap = st.camera_input("Fotoğraf Çekin:", key="camera_input_widget")

    if cam_snap:
        cam_bytes = cam_snap.getvalue()
        cam_hash = hashlib.md5(cam_bytes).hexdigest()

        if cam_hash not in st.session_state.seen_hashes:
            img = Image.open(cam_snap)
            cam_count = len([p for p in st.session_state.photo_pool if p["source"] == "Kamera"]) + 1
            photo_name = f"Kamera_Cekim_{cam_count}.jpg"

            with st.spinner("🔎 Fotoğraf üzerinde OCR ile CAS numarası aranıyor..."):
                extracted_cas = ocr.extract_cas_from_image(img, get_ocr_reader())

            st.session_state.photo_pool.append({
                "id": str(uuid.uuid4()),
                "hash": cam_hash,
                "name": photo_name,
                "image": img,
                "source": "Kamera",
                "extracted_cas": extracted_cas
            })
            st.session_state.seen_hashes.add(cam_hash)
            st.session_state.analysis_df = None
            st.success(f"✅ {photo_name} kümülatif havuza eklendi!")

# --- TAB 3: CAS NUMARASINDAN DOĞRUDAN RAPOR ---
if aktif_sekme == SEKMELER[2]:
    st.markdown("""
    <div class="scanner-viewfinder-box">
        <div class="scanner-guide-label">
            🧪 Fotoğraf Olmadan: CAS Numarasını Yazın, Raporu Anında Oluşturun
        </div>
    </div>
    """, unsafe_allow_html=True)

    cas_input = st.text_input(
        "CAS Numarası:",
        placeholder="Örn: 67-64-1",
        key="cas_manual_input"
    )
    btn_cas_report = st.button("📄 Rapor Oluştur ve Havuza Ekle", type="primary", use_container_width=True, key="cas_report_btn")

    # Havuza ekleme sonrası gösterilecek bilgi mesajı (bir kez gösterilir)
    if st.session_state.get("cas_mesaj"):
        st.success(st.session_state.pop("cas_mesaj"))

    if btn_cas_report:
        girilen_cas = (cas_input or "").strip().replace(" ", "")

        if not girilen_cas:
            st.warning("⚠️ Lütfen bir CAS numarası yazın.")
            st.session_state.cas_report = None
        elif not ocr.is_valid_cas(girilen_cas):
            st.error(f"❌ '{girilen_cas}' geçerli bir CAS numarası değil. Doğru format örneği: 7732-18-5")
            st.session_state.cas_report = None
        else:
            with st.spinner("🔍 MongoDB Atlas'ta MSDS kaydı aranıyor..."):
                sonuc, db_doc = cas_analiz_et(girilen_cas, get_mongo_collection(), selected_F)
            st.session_state.cas_report = {
                "sonuc": sonuc,
                "doc": db_doc,
                "lab": lab_choice,
                "tarih": time.strftime("%d.%m.%Y %H:%M")
            }

            # Bulunan kimyasalı ORTAK HAVUZA ekle (fotoğraf/kamera ile aynı havuz)
            if db_doc is not None:
                manuel_hash = f"manuel:{girilen_cas}"
                if manuel_hash in st.session_state.seen_hashes:
                    st.info(f"ℹ️ {sonuc['Kimyasal Adı']} zaten havuzda.")
                else:
                    st.session_state.photo_pool.append({
                        "id": str(uuid.uuid4()),
                        "hash": manuel_hash,
                        "name": "— (Manuel giriş)",
                        "image": None,
                        "source": "Manuel",
                        "extracted_cas": girilen_cas
                    })
                    st.session_state.seen_hashes.add(manuel_hash)
                    st.session_state.analysis_df = None
                    # Sol paneldeki sayaç da güncellensin diye sayfayı yeniden çiz
                    st.session_state.cas_mesaj = (
                        f"✅ {sonuc['Kimyasal Adı']} ortak havuza eklendi. Aşağıdaki "
                        f"'Toplu Risk Analizini Başlat' ile fotoğraflarla birlikte tek Excel'de raporlayabilirsin."
                    )
                    st.rerun()

    rapor = st.session_state.cas_report
    if rapor:
        sonuc = rapor["sonuc"]
        db_doc = rapor["doc"]

        if db_doc is None:
            if mongo_collection is None:
                st.warning("⚠️ MongoDB bağlantısı yok (Lokal Mod). Rapor oluşturmak için veritabanı bağlantısı gerekiyor.")
            else:
                st.warning(f"⚠️ `{sonuc['CAS Numarası']}` CAS numaralı kimyasal veritabanında bulunamadı.")
        else:
            # Risk derecesine göre rozet rengi (risk_hesap.risk_level_calculator çıktıları)
            risk_renkleri = {
                "Kabul Edilebilir Risk": "#34d399",
                "Dikkate Değer Risk": "#fbbf24",
                "Önemli Risk": "#fb923c",
                "Yüksek Risk": "#f87171",
                "Çok Yüksek Risk (Acil Eylem)": "#ef4444",
            }
            renk = risk_renkleri.get(sonuc["Risk Derecesi"], "#c7d2fe")

            st.markdown(f"""
            <div class="cas-report-card">
                <p class="cas-report-title">🧪 {sonuc['Kimyasal Adı']}</p>
                <p class="cas-report-sub">CAS: {sonuc['CAS Numarası']} &nbsp;·&nbsp; {rapor['lab']} &nbsp;·&nbsp; Rapor Tarihi: {rapor['tarih']}</p>
                <div class="cas-risk-badge" style="color: {renk}; border-color: {renk}; background: {renk}22;">Risk Derecesi: {sonuc['Risk Derecesi']}</div>
            </div>
            """, unsafe_allow_html=True)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Olasılık (O)", f"{sonuc['Olasılık (O)']:g}")
            m2.metric("Şiddet (S)", f"{sonuc['Şiddet (S)']:g}")
            m3.metric("Frekans (F)", f"{sonuc['Frekans (F)']:g}")
            m4.metric("Fine Kinney Skoru", f"{sonuc['Fine Kinney Skoru']:g}")

            # msds_okuma.py'nin veritabanına yazdığı ek alanlar
            fiziksel_hal = db_doc.get("fiziksel_hal") or "Tespit edilemedi"
            kaynak_dosya = db_doc.get("dosya_kaynagi") or "—"
            st.markdown(f"**🧊 Fiziksel Hal:** {fiziksel_hal} &nbsp;&nbsp;|&nbsp;&nbsp; **📄 Kaynak MSDS:** {kaynak_dosya}")
            if db_doc.get("olasilik_puani") in (None, ""):
                st.caption("ℹ️ Fiziksel hal MSDS'ten okunamadığı için Olasılık (O) için güvenli taraf varsayılanı (6) kullanıldı.")

            def ifade_tablosu(liste):
                """[{'kod':..., 'aciklama':...}] listesini Kod/Açıklama tablosuna çevirir."""
                satirlar = []
                for x in (liste or []):
                    if isinstance(x, dict):
                        satirlar.append({"Kod": x.get("kod", ""), "Açıklama": x.get("aciklama", "")})
                    else:
                        satirlar.append({"Kod": str(x), "Açıklama": ""})
                return pd.DataFrame(satirlar, columns=["Kod", "Açıklama"])

            h_df = ifade_tablosu(db_doc.get("h_ifadeleri"))
            p_df = ifade_tablosu(db_doc.get("p_ifadeleri"))

            st.markdown("#### ⚠️ Tehlike İfadeleri (H Kodları)")
            if not h_df.empty:
                st.dataframe(h_df, hide_index=True, use_container_width=True)
            else:
                st.info("Bu kimyasal için kayıtlı H ifadesi yok.")

            st.markdown("#### 🛡️ Önlem İfadeleri (P Kodları)")
            if not p_df.empty:
                st.dataframe(p_df, hide_index=True, use_container_width=True)
            else:
                st.info("Bu kimyasal için kayıtlı P ifadesi yok.")

            # Veritabanındaki kaydın tamamı (MongoDB'ye özel _id alanı hariç)
            with st.expander("🗂️ Veritabanındaki MSDS kaydının tamamını göster"):
                temiz_kayit = {
                    k: (v if isinstance(v, (str, int, float, bool, list, dict, type(None))) else str(v))
                    for k, v in db_doc.items() if k != "_id"
                }
                st.json(temiz_kayit)

            # Sadece bu kimyasalın Excel'i (resmi Fine Kinney tablosu düzeni)
            st.download_button(
                label="📄 Sadece Bu Kimyasalın Excel'ini İndir (.xlsx)",
                data=fine_kinney_excel([cas_excel_satiri(sonuc, db_doc, rapor["lab"])]),
                file_name=f"Fine_Kinney_Risk_Analizi_{sonuc['CAS Numarası']}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="cas_report_download"
            )

st.markdown("---")

# ==============================================================================
# 7. KÜMÜLATİF KİMYASAL HAVUZU GALERİSİ & TEKİL SİLME
#    (Dosya, Kamera ve Manuel CAS girişleri aynı havuzda toplanır)
# ==============================================================================
st.subheader("🖼️ Kümülatif Kimyasal Havuzu (Fotoğraf, Kamera ve Manuel Girişler)")

if st.session_state.photo_pool:
    cols_per_row = 4
    pool = st.session_state.photo_pool
    to_delete_id = None

    for i in range(0, len(pool), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, item in enumerate(pool[i:i+cols_per_row]):
            with cols[j]:
                if item.get("image") is not None:
                    st.image(item["image"], use_container_width=True)
                    st.caption(f"📌 {item['name']} ({item['source']})")
                else:
                    # Manuel CAS girişi: fotoğraf yerine bilgi kartı
                    st.markdown(f"""
                    <div class="manual-cas-card">
                        <div class="ikon">🧪</div>
                        <div class="cas">{item['extracted_cas']}</div>
                        <div class="etiket">Manuel CAS Girişi</div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.caption("📌 Manuel giriş")
                if item["source"] == "Manuel":
                    st.caption(f"✅ CAS: `{item['extracted_cas']}`")
                elif item.get("extracted_cas"):
                    st.caption(f"✅ OCR CAS: `{item['extracted_cas']}`")
                else:
                    st.caption("⚠️ OCR: CAS bulunamadı")

                if st.button("🗑️ Sil", key=f"delete_btn_{item['id']}", use_container_width=True):
                    to_delete_id = item["id"]

    if to_delete_id:
        item_to_remove = next((x for x in st.session_state.photo_pool if x["id"] == to_delete_id), None)
        if item_to_remove:
            st.session_state.photo_pool.remove(item_to_remove)
            if item_to_remove.get("hash") in st.session_state.seen_hashes:
                st.session_state.seen_hashes.remove(item_to_remove["hash"])
            st.session_state.analysis_df = None
            st.rerun()
else:
    st.info("💡 Yukarıdaki sekmelerden fotoğraf yükleyin, kameradan fotoğraf çekin veya CAS numarasını elle girin. Hepsi bu ortak havuzda toplanır ve tek bir Excel'de raporlanır.")

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# 8. GERÇEK MONGODB ATLAS ENTEGRASYONU VE DÜZENLENEBİLİR TABLO (st.data_editor)
# ==============================================================================
col_action_btn, _ = st.columns([2, 1])

with col_action_btn:
    if len(st.session_state.photo_pool) > 0:
        btn_start_batch = st.button("🚀 Toplu Risk Analizini Başlat ", type="primary", use_container_width=True)
    else:
        btn_start_batch = st.button("🚀 Toplu Risk Analizini Başlat ", disabled=True, use_container_width=True)

if btn_start_batch and st.session_state.photo_pool:
    with st.spinner("🔍 MongoDB Atlas veritabanından CAS Numaraları ve MSDS kayıtları çekiliyor..."):
        time.sleep(0.6)

    collection = get_mongo_collection()
    rows_data = []

    for idx, item in enumerate(st.session_state.photo_pool):
        # CAS Numarası: OCR'dan (Dosya/Kamera) veya elle girilen (Manuel) gerçek değer
        sonuc, doc = cas_analiz_et(item.get("extracted_cas"), collection, selected_F)
        if doc:
            st.session_state.msds_cache[doc.get("cas_no", sonuc["CAS Numarası"])] = {
                "h_ifadeleri": doc.get("h_ifadeleri"),
                "p_ifadeleri": doc.get("p_ifadeleri"),
                "fiziksel_hal": doc.get("fiziksel_hal"),
            }

        row = {
            "Sıra No": idx + 1,
            "Fotoğraf Adı": item["name"],
            "Kaynak": item["source"],
        }
        row.update(sonuc)
        rows_data.append(row)

    st.session_state.analysis_df = pd.DataFrame(rows_data)

# DISPLAY EDITABLE TABLE & DOWNLOAD IF ANALYSIS HAS BEEN RUN
if st.session_state.analysis_df is not None and not st.session_state.analysis_df.empty:
    st.markdown("""<div class="editor-container-box">""", unsafe_allow_html=True)
    st.subheader("📝 Düzenlenebilir Fine Kinney Risk Analizi Tablosu")
    st.caption("💡 İpucu: Tablodaki tüm değerlere (CAS No, Kimyasal Adı, O, S, F) tıklayarak manuel değişiklikler yapabilirsiniz. Skorlar ve risk dereceleri otomatik güncellenir.")

    # STREAMLIT DYNAMIC INTERACTIVE DATA EDITOR (st.data_editor)
    edited_df = st.data_editor(
        st.session_state.analysis_df,
        num_rows="dynamic",
        use_container_width=True,
        key="fine_kinney_data_editor"
    )

    # Dynamically Recalculate Fine Kinney Score & Risk Level if user edits O, S, or F
    if all(col in edited_df.columns for col in ["Olasılık (O)", "Şiddet (S)", "Frekans (F)"]):
        o_vals = edited_df["Olasılık (O)"].apply(lambda v: risk_hesap.safe_float(v, default=6.0))
        s_vals = edited_df["Şiddet (S)"].apply(lambda v: risk_hesap.safe_float(v, default=15.0))
        f_vals = edited_df["Frekans (F)"].apply(lambda v: risk_hesap.safe_float(v, default=selected_F))
        edited_df["Fine Kinney Skoru"] = o_vals * s_vals * f_vals
        edited_df["Risk Derecesi"] = edited_df["Fine Kinney Skoru"].apply(risk_hesap.risk_level_calculator)

    st.markdown("""</div>""", unsafe_allow_html=True)

    # Resmi Fine Kinney Risk Analizi Tablosu düzeninde Excel (DÜZENLENMİŞ tablodan)
    def metin(v):
        """NaN/None değerleri boş metne çevirir."""
        return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()

    bolum = lab_choice.split(" (")[0]
    excel_satirlari = []
    for _, satir in edited_df.iterrows():
        cas = metin(satir.get("CAS Numarası"))
        ad = metin(satir.get("Kimyasal Adı"))
        if not cas and not ad:
            continue  # tamamen boş eklenmiş satırları atla
        kayit = st.session_state.msds_cache.get(cas)
        if kayit:
            tehlike = tehlike_tanimi(ad, cas, kayit.get("fiziksel_hal"))
            risk = ifade_metni(kayit.get("h_ifadeleri"), "Sınıflandırılmış tehlike (H) ifadesi yok")
            aksiyon = ifade_metni(kayit.get("p_ifadeleri"), "MSDS'te kayıtlı önlem (P) ifadesi yok")
        else:
            tehlike = tehlike_tanimi(ad or "Bilinmeyen Kimyasal", cas or "—")
            risk = metin(satir.get("H Tehlike Kodları"))
            aksiyon = ""
        excel_satirlari.append({
            "bolum": bolum,
            "tehlike": tehlike,
            "risk": risk,
            "aksiyon": aksiyon,
            "olasilik": satir.get("Olasılık (O)"),
            "siddet": satir.get("Şiddet (S)"),
            "frekans": satir.get("Frekans (F)"),
        })

    st.markdown("<br>", unsafe_allow_html=True)
# ==============================================================================
    # 🌍 ÇEVRE BİLİNÇLENDİRME VE ONAY EKRANI
    # ==============================================================================
    if not st.session_state.show_report_warning:
        # Kullanıcı henüz onaya basmadıysa sadece Rapor Oluştur butonunu göster
        if st.button("📊 Nihai Raporu Oluştur", type="primary", use_container_width=True):
            st.session_state.show_report_warning = True
            st.rerun()
    else:
        # Butona basıldıysa Uyarı ve Onay Ekranını Göster
        st.markdown("""
        <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.4); padding: 1.5rem; border-radius: 12px; margin-bottom: 1rem; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
            <h3 style="color: #34d399; margin-top: 0; display: flex; align-items: center; gap: 8px;">
                🌍 Doğayı ve Geleceği Korumak Elimizde
            </h3>
            <p style="color: #e2e8f0; font-size: 0.95rem; line-height: 1.6; margin-bottom: 0;">
                Risk analiziniz tamamlandı ve raporunuz oluşturulmak üzere. Lütfen unutmayın: Kimyasalların güvenli kullanımı sadece laboratuvarı değil, dünyamızı da korur. Hatalı bertaraf edilen her kimyasal, ekosistemde geri dönüşü olmayan izler bırakır. Atıklarınızı uygun İSG ve Çevre prosedürlerine göre yönettiğinizden emin olun.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Yan yana iki buton: Raporu İndir (Vurgulu) ve Geri Dön (Gri)
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            # Excel'i İndiren Ana Buton
            st.download_button(
                label="✅ Raporu Oluştur ve Çık",
                data=fine_kinney_excel(excel_satirlari),
                file_name="Fine_Kinney_Toplu_Risk_Analizi.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary"
            )
            
    