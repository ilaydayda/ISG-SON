import streamlit as st
from PIL import Image
import pandas as pd
from pillow_heif import register_heif_opener
import io
import time
import uuid
import hashlib

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

# Dark Corporate Theme CSS
st.markdown("""
<style>
    .stApp {
        background-color: #090d16;
        background-image:
            radial-gradient(circle at 10% 10%, rgba(99, 102, 241, 0.08) 0%, transparent 40%),
            radial-gradient(circle at 90% 90%, rgba(6, 182, 212, 0.06) 0%, transparent 40%);
        color: #f8fafc;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Executive Header */
    .executive-header {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.85));
        border: 1px solid rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(16px);
        padding: 1.25rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 10px 30px rgba(0,0,0,0.4);
    }
    .header-title-text {
        font-size: 1.45rem;
        font-weight: 800;
        background: linear-gradient(to right, #ffffff, #cbd5e1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .header-subtitle-text {
        font-size: 0.82rem;
        color: #94a3b8;
        margin-top: 0.2rem;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(15, 23, 42, 0.7);
        padding: 6px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .stTabs [data-baseweb="tab"] {
        height: 46px;
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 600;
        font-size: 0.88rem;
        background-color: transparent;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #6366f1 !important;
        color: #ffffff !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
    }

    /* Scanner Viewfinder Box */
    .scanner-viewfinder-box {
        border: 2px dashed #06b6d4;
        border-radius: 14px;
        background: rgba(6, 182, 212, 0.04);
        padding: 0.85rem;
        text-align: center;
        margin-bottom: 1rem;
        box-shadow: inset 0 0 20px rgba(6, 182, 212, 0.08);
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
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 16px;
        padding: 1.5rem;
        margin-top: 1.5rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. ÖNBELLEKLİ KAYNAKLAR (MongoDB bağlantısı & EasyOCR modeli)
# ==============================================================================
@st.cache_resource
def get_mongo_collection():
    """MongoDB Atlas bağlantısını Streamlit oturumu boyunca önbellekte tutar."""
    return db.get_collection()

@st.cache_resource
def get_ocr_reader():
    """EasyOCR modelini bir kez yükleyip önbellekte tutar (ağır/yavaş bir işlem)."""
    return ocr.create_reader()

# ==============================================================================
# 3. SESSION STATE (STATE MİMARİSİ)
# ==============================================================================
if "photo_pool" not in st.session_state:
    st.session_state.photo_pool = []

if "seen_hashes" not in st.session_state:
    st.session_state.seen_hashes = set()

if "analysis_df" not in st.session_state:
    st.session_state.analysis_df = None

# ==============================================================================
# 4. HEADER (ÜST BİLGİ ALANI VE MONGODB BAĞLANTI DURUMU)
# ==============================================================================
mongo_collection = get_mongo_collection()
db_status_color = "#34d399" if mongo_collection is not None else "#fbbf24"
db_status_text = "● MongoDB Atlas Bağlandı" if mongo_collection is not None else "● MongoDB Çevrimdışı (Lokal Mod)"

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
        <span style="font-size: 0.85rem; font-weight: 600; color: #94a3b8;">Havuzdaki Toplam Şişe</span>
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
# 6. ANA EKRAN (SEKMELİ YÜKLEME & HASH KORUMALI KAMERA ÇEKİMİ)
# ==============================================================================
tab_upload, tab_camera = st.tabs(["📁 Dosyadan Yükle (Çoklu)", "📸 Sınırsız Canlı Kamera Taraması"])

# --- TAB 1: ÇOKLU DOSYA YÜKLEME ---
with tab_upload:
    uploaded_files = st.file_uploader(
        "Birden fazla şişe/etiket fotoğrafı seçin (Yüklenen fotoğraflar klonlanmadan havuza eklenir):",
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
with tab_camera:
    st.markdown("""
    <div class="scanner-viewfinder-box">
        <div class="scanner-guide-label">
            🎯 CAS Numarasını Ekran Ortasındaki Kılavuz Çerçeveye Hizalayın
        </div>
    </div>
    """, unsafe_allow_html=True)

    cam_snap = st.camera_input("Fotoğraf Çekin (Klonlama yapılmadan çekimler havuza eklenir):", key="camera_input_widget")

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

st.markdown("---")

# ==============================================================================
# 7. KÜMÜLATİF FOTOĞRAF HAVUZU GALERİSİ & TEKİL SİLME
# ==============================================================================
st.subheader("🖼️ Kümülatif Fotoğraf Havuzu (Listelenen Şişeler)")

if st.session_state.photo_pool:
    cols_per_row = 4
    pool = st.session_state.photo_pool
    to_delete_id = None

    for i in range(0, len(pool), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, item in enumerate(pool[i:i+cols_per_row]):
            with cols[j]:
                st.image(item["image"], use_container_width=True)
                st.caption(f"📌 {item['name']} ({item['source']})")
                if item.get("extracted_cas"):
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
    st.info("💡 Yukarıdaki sekmelerden fotoğraf yükleyin veya kameradan fotoğraf çekin. Görseller klonlanmadan havuza eklenir.")

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# 8. GERÇEK MONGODB ATLAS ENTEGRASYONU VE DÜZENLENEBİLİR TABLO (st.data_editor)
# ==============================================================================
col_action_btn, _ = st.columns([2, 1])

with col_action_btn:
    if len(st.session_state.photo_pool) > 0:
        btn_start_batch = st.button("🚀 Toplu Risk Analizini Başlat (MongoDB Atlas)", type="primary", use_container_width=True)
    else:
        btn_start_batch = st.button("🚀 Toplu Risk Analizini Başlat (MongoDB Atlas)", disabled=True, use_container_width=True)

if btn_start_batch and st.session_state.photo_pool:
    with st.spinner("🔍 MongoDB Atlas veritabanından CAS Numaraları ve MSDS kayıtları çekiliyor..."):
        time.sleep(0.6)

    collection = get_mongo_collection()
    rows_data = []

    for idx, item in enumerate(st.session_state.photo_pool):
        # 1. CAS Numarasını Belirle (yalnızca dosya adından/OCR'dan çıkarılan gerçek değer)
        target_cas = item.get("extracted_cas")
        cas_valid = ocr.is_valid_cas(target_cas)

        db_doc = None
        if cas_valid and collection is not None:
            try:
                # MongoDB Atlas sorgusu: {"cas_no": target_cas}
                db_doc = collection.find_one({"cas_no": target_cas})
            except Exception as e:
                db_doc = None

        # 2. MongoDB Verilerini İşle veya Bulunamadı Durumunu Net Şekilde İşaretle
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

            score = olasilik * siddet * selected_F
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

        rows_data.append({
            "Sıra No": idx + 1,
            "Fotoğraf Adı": item["name"],
            "Kaynak": item["source"],
            "CAS Numarası": display_cas,
            "Kimyasal Adı": chem_name,
            "H Tehlike Kodları": h_codes_str,
            "Olasılık (O)": olasilik,
            "Şiddet (S)": siddet,
            "Frekans (F)": selected_F,
            "Fine Kinney Skoru": score,
            "Risk Derecesi": deg
        })

    st.session_state.analysis_df = pd.DataFrame(rows_data)

# DISPLAY EDITABLE TABLE & DOWNLOAD IF ANALYSIS HAS BEEN RUN
if st.session_state.analysis_df is not None and not st.session_state.analysis_df.empty:
    st.markdown("""<div class="editor-container-box">""", unsafe_allow_html=True)
    st.subheader("📝 Düzenlenebilir Fine Kinney Risk Analizi Tablosu (MongoDB Atlas Entegreli)")
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

    # Generate Excel Download Buffer from EDITED DataFrame
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        edited_df.to_excel(writer, index=False, sheet_name="Fine Kinney Raporu")

    st.markdown("<br>", unsafe_allow_html=True)

    # Download Button for the updated edited DataFrame
    st.download_button(
        label="📊 Düzenlenmiş Fine Kinney Excel Raporunu İndir (.xlsx)",
        data=excel_buffer.getvalue(),
        file_name="Fine_Kinney_Toplu_Risk_Analizi.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary"
    )
