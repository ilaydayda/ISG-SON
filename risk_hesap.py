"""Fine Kinney risk hesaplama katmanı: H kodundan Şiddet puanı çıkarma,
skor (Olasılık x Şiddet x Frekans) ve Risk Derecesi hesaplama, güvenli
sayısal dönüşüm."""
import re

# Standard H-code Severity Mapping Rule (MAX Rule Engine)
H_SEVERITY_MAP = {
    "H350": 40, "H340": 40, "H300": 40, "H310": 40, "H330": 40, "H370": 40,
    "H314": 40, "H318": 40, "H301": 40, "H311": 40, "H331": 40, "H372": 40, "H373": 40,
    "H225": 15, "H224": 15, "H290": 15, "H302": 15, "H312": 15, "H332": 15, "H315": 15, "H319": 15,
    "H304": 7,  "H317": 7,  "H335": 7,  "H336": 7
}


def calculate_max_severity(h_codes_list):
    """En Kötü Senaryo (MAX) Kuralına göre Şiddet (S) puanı hesaplar.
    Birleşik kodlar (örn. 'H301+H311+H331') ve harf ekli varyantlar
    (örn. 'H360FD', 'H350i') temel kodlarına ayrılarak tek tek değerlendirilir."""
    severities = []
    for code in h_codes_list:
        for temel_kod in re.findall(r"H\d{3}", str(code).upper()):
            severities.append(H_SEVERITY_MAP.get(temel_kod, 15))
    return max(severities) if severities else 15


def risk_level_calculator(score):
    """Fine Kinney Skoruna göre Risk Derecesi atar"""
    try:
        score_val = float(score)
        if score_val < 20: return "Kabul Edilebilir Risk"
        elif score_val < 70: return "Dikkate Değer Risk"
        elif score_val < 200: return "Önemli Risk"
        elif score_val < 400: return "Yüksek Risk"
        else: return "Çok Yüksek Risk (Acil Eylem)"
    except:
        return "Bilinmiyor"


def safe_float(value, default=6.0):
    """Veritabanından/kullanıcıdan gelen değeri güvenle float'a çevirir.
    Boş string, None veya sayısal olmayan değerlerde İSG 'Güvenli Tarafta Kalma'
    ilkesi gereği varsayılan (default) değeri döndürür."""
    if value is None:
        return default
    if isinstance(value, str) and value.strip() == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default