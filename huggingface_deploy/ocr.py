"""Görüntü işleme + OCR katmanı: şişe/etiket fotoğraflarından CAS numarası okuma.

EasyOCR ile üç farklı ön işleme yöntemi (düz büyütme, Otsu eşikleme,
keskinleştirme) dener, 'CAS' etiketinin yakınındaki metne öncelik verir ve
sık OCR hatalarını (l->1, O->0, eksik tire) düzeltir. Bulduğu her aday,
kesin kabulden önce katı CAS regex'inden geçirilir; hiçbir zaman rastgele/
uydurma bir değer üretmez."""
import re
import numpy as np
import cv2

CAS_REGEX = re.compile(r'^\d{2,7}-\d{2}-\d$')
CAS_SEARCH_REGEX = re.compile(r'\d{2,7}-\d{2}-\d')


def is_valid_cas(cas_value):
    """Verilen CAS numarasının katı formata uyup uymadığını kontrol eder."""
    return bool(cas_value) and bool(CAS_REGEX.match(cas_value.strip()))


def create_reader():
    """Yeni bir EasyOCR Reader nesnesi oluşturur (ağır/yavaş bir işlem).
    Çağıran taraf (örn. Streamlit'te st.cache_resource) bunu önbelleğe almalı,
    her fotoğraf için yeniden oluşturmamalı."""
    import easyocr  # Geç import: uygulama başlarken PyTorch yüklemesini önler
    return easyocr.Reader(['en'], gpu=False)


def _tire_duzelt(metin):
    """OCR'ın kaçırdığı ikinci tireyi tamamlar: '141-786' -> '141-78-6'."""
    parcalar = metin.split("-")
    if len(parcalar) == 2 and len(parcalar[1]) > 2:
        return f"{parcalar[0]}-{parcalar[1][:2]}-{parcalar[1][2:]}"
    return metin


def _cas_adayi_ayikla(metin):
    """Tek bir OCR metin parçasından CAS adayı çıkarır: boşlukları siler,
    OCR'ın sık karıştırdığı harf/rakamları düzeltir (l->1, O->0) ve eksik
    tireyi tamamlamayı dener. Bulursa ham adayı döner (nihai format kontrolü
    çağıran tarafta is_valid_cas ile yapılır)."""
    metin_duz = metin.replace(" ", "").replace("l", "1").replace("O", "0")
    eslesen = CAS_SEARCH_REGEX.search(metin_duz)
    if eslesen:
        return eslesen.group()
    eslesen = CAS_SEARCH_REGEX.search(_tire_duzelt(metin_duz))
    if eslesen:
        return eslesen.group()
    return None


def extract_cas_from_image(pil_image, reader):
    """Görsel üzerinde gerçek OCR (EasyOCR) ile CAS numarası arar.
    Üç farklı görüntü işleme yöntemini (büyütme, Otsu eşikleme, keskinleştirme)
    dener ve etikette 'CAS' yazan satırın hizasındaki/yakınındaki metne bakarak
    numarayı bulmaya çalışır. Bulamazsa None döner; asla rastgele/uydurma
    değer üretmez — nihai kabul her zaman is_valid_cas ile katı şekilde denetlenir.

    reader: create_reader() ile oluşturulmuş (ve çağıran tarafça önbelleklenmiş)
    bir easyocr.Reader nesnesi."""
    try:
        img_array = np.array(pil_image.convert('RGB'))
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        # Küçük detayların ortaya çıkması için büyüt; ancak telefon kamerasından
        # gelen yüksek çözünürlüklü fotoğrafların OCR'ı donduracak kadar
        # devasa büyümesini önlemek için oranı görüntü boyutuna göre sınırla.
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

            # 1) "CAS" yazan satırları bul (EC-No satırlarını hariç tut)
            cas_satirlari_y = []
            for (bbox, metin, guven) in sonuclar:
                metin_upper = metin.upper().replace(" ", "")
                if "CAS" in metin_upper and "EC" not in metin_upper and guven > 0.2:
                    cas_y = (bbox[0][1] + bbox[2][1]) / 2
                    cas_satirlari_y.append(cas_y)
                    aday = _cas_adayi_ayikla(metin)
                    if aday:
                        bulunan.append(aday)

            # 2) "CAS" satırının dikey hizasındaki (80px içindeki) diğer metinlere bak
            for cas_y in cas_satirlari_y:
                for (bbox2, metin2, guven2) in sonuclar:
                    if guven2 < 0.2:
                        continue
                    metin2_y = (bbox2[0][1] + bbox2[2][1]) / 2
                    if abs(metin2_y - cas_y) < 80:
                        aday = _cas_adayi_ayikla(metin2)
                        if aday:
                            bulunan.append(aday)

            # 3) Hiçbir şey bulunamadıysa tüm metinlerde ara (daha düşük güven eşiği)
            if not bulunan:
                for (_bbox, metin, guven) in sonuclar:
                    if guven < 0.3:
                        continue
                    aday = _cas_adayi_ayikla(metin)
                    if aday:
                        bulunan.append(aday)

            # Katı format kontrolünden geçen ilk adayı kabul et (EC-No'lar farklı
            # basamak yapısına sahip olduğundan CAS_REGEX'i zaten geçemez)
            gecerli_adaylar = [b for b in bulunan if is_valid_cas(b)]
            if gecerli_adaylar:
                return gecerli_adaylar[0]

        return None
    except Exception:
        return None
