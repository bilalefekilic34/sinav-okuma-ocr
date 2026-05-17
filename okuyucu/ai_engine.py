import os
import re
import sys
import io
import tempfile
import joblib
import pandas as pd
import traceback
import time
from rapidocr_onnxruntime import RapidOCR

# --- PyMuPDF (PDF Desteği) Kontrolü ---
try:
    import fitz  # PyMuPDF
    PYMUPDF_MEVCUT = True
except ImportError:
    PYMUPDF_MEVCUT = False
    print("⚠️ [UYARI] PyMuPDF (fitz) bulunamadı. PDF desteği devre dışı.", flush=True)

class SinavMotoru:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SinavMotoru, cls).__new__(cls)
            cls._instance._baslat()
        return cls._instance

    def _baslat(self):
        print("\n" + "="*60, flush=True)
        print("🚀 [SİSTEM] RapidOCR (Yön Farkındalıklı & Adil Geometrik) Motor Başlatılıyor...", flush=True)
        print("="*60, flush=True)
        
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        pkl_yolu = os.path.join(self.BASE_DIR, "ogrenci_analiz_modeli.pkl")
        try:
            self.ml_model = joblib.load(pkl_yolu)
            print("✅ [DEBUG] 1. Adım Tamamlandı: ML Modeli Yüklendi!", flush=True)
        except Exception as e:
            self.ml_model = None
            print(f"⚠️ [DEBUG] HATA: .pkl dosyası bulunamadı! Detay: {e}", flush=True)
        
        try:
            self.ocr_model = RapidOCR()
            print("✅ [DEBUG] 2. Adım Tamamlandı: RapidOCR Başarıyla Yüklendi!", flush=True)
        except Exception as e:
            print("\n❌ [DEBUG] KRİTİK HATA: RapidOCR yüklenirken çöktü!", flush=True)
            traceback.print_exc()
            raise e

        print("="*60 + "\n", flush=True)

    def kagidi_oku_ve_degerlendir(self, resim_yolu):
        raw_output = ""
        headers_info = []
        scores_info = []
        soru_sayisi = 5 

        try:
            result, elapse = self.ocr_model(resim_yolu)
            raw_lines = []
            
            if result:
                for box_info in result:
                    coords = box_info[0] 
                    text = box_info[1].strip()
                    text_clean = text.upper()
                    
                    # 💡 OCR'ın 'O', 'o', 'Q' harflerini 0 sanma düzeltmesi
                    if text_clean in ['O', 'Q', 'C', 'D'] and len(text_clean) == 1:
                        text_clean = '0'
                        
                    raw_lines.append(text_clean)
                    
                    x_center = sum([p[0] for p in coords]) / 4
                    y_center = sum([p[1] for p in coords]) / 4

                    # --- 1. Başlıkları Yakala ---
                    m_q = re.match(r'^S(?:ORU)?\s*([L1-9][0-9]*|S)$', text_clean)
                    if m_q:
                        q_num = m_q.group(1)
                        if q_num == 'L': q_num = '1'  
                        if q_num == 'S': q_num = '5'  
                        headers_info.append({'id': q_num, 'x': x_center, 'y': y_center})
                    elif re.search(r'TOPLAM|TOPLORN|PUAN', text_clean):
                        headers_info.append({'id': 'TOPLAM', 'x': x_center, 'y': y_center})

                    # --- 2. Sayıları Yakala ---
                    elif text_clean.isdigit():
                        scores_info.append({'val': int(text_clean), 'str': text_clean, 'x': x_center, 'y': y_center})
                        
            raw_output = "\n".join(raw_lines)
            print("\n🔍 --- RAPIDOCR GÖZÜNDEN OKUNAN TEMİZ METİN ---", flush=True)
            print(raw_output if raw_output.strip() else "[Boş Çıktı - Metin Bulunamadı]", flush=True)
            print("------------------------------------------------\n", flush=True)
            
        except Exception as e:
            print(f"⚠️ OCR Okuma Hatası: {str(e)}", flush=True)

        okunan_veriler = {"sinav_id": "00000", "ogrenci_no": "0000", "sorular": {}, "toplam_puan": 0}

        s_id_match = re.search(r'\b(\d{5})\b', raw_output)
        if s_id_match: okunan_veriler["sinav_id"] = s_id_match.group(1)

        o_no_match = re.findall(r'\b(\d{4})\b', raw_output)
        for m in o_no_match:
            if m not in ['1024', '1280', '2048']:
                okunan_veriler["ogrenci_no"] = m
                break

        # ==============================================================================
        # 📐 DİNAMİK YÖN (ORIENTATION) VE EŞLEŞTİRME ALGORİTMASI
        # ==============================================================================
        if headers_info:
            soru_numaralari = [int(h['id']) for h in headers_info if h['id'].isdigit()]
            if soru_numaralari: soru_sayisi = max(soru_numaralari)
        
        print(f"📏 [BİLGİ] Dinamik Soru Sayısı Algılandı: {soru_sayisi} Soru", flush=True)

        is_horizontal = True
        if len(headers_info) > 1:
            hx = [h['x'] for h in headers_info]
            hy = [h['y'] for h in headers_info]
            if (max(hy) - min(hy)) > (max(hx) - min(hx)):
                is_horizontal = False 
                
        print(f"📐 [BİLGİ] Tablo Yönü: {'Yatay (Horizontal)' if is_horizontal else 'Dikey (Vertical)'}", flush=True)

        valid_scores = []
        for s in scores_info:
            val = s['val']
            if val in [int(okunan_veriler.get("sinav_id", 0)), int(okunan_veriler.get("ogrenci_no", 0)), 1024, 1280, 2048]:
                continue
                
            # 💥 ÖĞRETMEN ZEKASI DÜZELTİLDİ: Sadece 70 ile 79 arasındaysa 60 çıkar (74 -> 14).
            # Öğrencinin gerçekten aldığı 7 puana dokunmaz!
            if 70 <= val <= 79:
                val = val - 60
                
            valid_scores.append({'val': val, 'x': s['x'], 'y': s['y']})

        if headers_info:
            for v in valid_scores:
                if is_horizontal:
                    closest_header = min(headers_info, key=lambda h: abs(h['x'] - v['x']))
                else:
                    closest_header = min(headers_info, key=lambda h: abs(h['y'] - v['y']))
                
                # Kapasite sınırı
                if closest_header['id'] != 'TOPLAM' and v['val'] <= 20:
                    okunan_veriler["sorular"][str(closest_header['id'])] = v['val']

        for i in range(1, soru_sayisi + 1):
            if str(i) not in okunan_veriler["sorular"]:
                okunan_veriler["sorular"][str(i)] = 0

        okunan_veriler["toplam_puan"] = sum(okunan_veriler["sorular"].values())
        
        try:
            if soru_sayisi == 5 and self.ml_model is not None:
                ML_beklenen_sutunlar = ['soru_1', 'soru_2', 'soru_3', 'soru_4', 'soru_5']
                ml_input = [okunan_veriler["sorular"].get(str(i), 0) for i in range(1, 6)]
                input_df = pd.DataFrame([ml_input], columns=ML_beklenen_sutunlar)
                tahmin = self.ml_model.predict(input_df)[0]
                okunan_veriler["yapay_zeka_karari"] = "Geçti" if tahmin == 1 else "Kaldı"
            else:
                okunan_veriler["yapay_zeka_karari"] = "Geçti" if okunan_veriler["toplam_puan"] >= 50 else "Kaldı"
        except Exception:
            okunan_veriler["yapay_zeka_karari"] = "Geçti" if okunan_veriler["toplam_puan"] >= 50 else "Kaldı"
            
        okunan_veriler["durum"] = "basarili" if okunan_veriler["sinav_id"] != "00000" else "hata"

        print(f"📊 [SONUÇ] Puanlar: {okunan_veriler['sorular']} | Toplam: {okunan_veriler['toplam_puan']}", flush=True)

        return okunan_veriler

    def pdf_isle(self, pdf_yolu):
        if not PYMUPDF_MEVCUT:
            return []
        sonuclar = []
        try:
            belge = fitz.open(pdf_yolu)
        except:
            return []

        for sayfa_no in range(len(belge)):
            gecici_dosya = None
            try:
                sayfa = belge[sayfa_no]
                piksel = sayfa.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    gecici_dosya = tmp.name
                piksel.save(gecici_dosya)
                sonuc = self.kagidi_oku_ve_degerlendir(gecici_dosya)
                sonuc["kaynak_dosya"] = os.path.basename(pdf_yolu)
                sonuc["pdf_sayfa_no"] = sayfa_no + 1
                sonuclar.append(sonuc)
            except:
                pass
            finally:
                if gecici_dosya and os.path.exists(gecici_dosya):
                    try: os.remove(gecici_dosya)
                    except: pass
        belge.close()
        return sonuclar

def dosyayi_isle(motor, dosya_yolu):
    uzanti = os.path.splitext(dosya_yolu)[1].lower()
    if uzanti in (".jpg", ".jpeg", ".png"):
        sonuc = motor.kagidi_oku_ve_degerlendir(dosya_yolu)
        sonuc.setdefault("kaynak_dosya", os.path.basename(dosya_yolu))
        sonuc.setdefault("pdf_sayfa_no", None)
        return [sonuc]
    elif uzanti == ".pdf":
        return motor.pdf_isle(dosya_yolu)
    else:
        return []

if __name__ == "__main__":
    motor = SinavMotoru()
    test_resmi = "test_veriseti_100/tablo_1007.jpg" 
    
    if os.path.exists(test_resmi):
        baslangic = time.time()
        sonuc = motor.kagidi_oku_ve_degerlendir(test_resmi)
        sure = time.time() - baslangic
        
        print("\n" + "="*50, flush=True)
        print(f"✅ [TEST BAŞARILI] Okuma tamamlandı! Süre: {sure:.2f} saniye", flush=True)
        print("="*50, flush=True)
    else:
        print(f"\n⚠️ HATA: Test için '{test_resmi}' dosyası bulunamadı. Lütfen yolu kontrol et.", flush=True)