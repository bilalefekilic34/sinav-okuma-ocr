import os
import torch
import re
import sys
import io
import tempfile
from transformers import AutoModel, AutoTokenizer, BitsAndBytesConfig
import joblib
import pandas as pd

try:
    import fitz  # PyMuPDF
    PYMUPDF_MEVCUT = True
except ImportError:
    PYMUPDF_MEVCUT = False
    print("⚠️ [UYARI] PyMuPDF (fitz) bulunamadı. PDF desteği devre dışı. Yüklemek için: pip install pymupdf")

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

class SinavMotoru:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SinavMotoru, cls).__new__(cls)
            cls._instance._baslat()
        return cls._instance

    def _baslat(self):
        print("\n🧠 [SİSTEM] Çevrimdışı Yapay Zeka Motorları Yükleniyor...")
        
        # --- UNUTULAN ML MODELİ YÜKLEME KISMI ---
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        pkl_yolu = os.path.join(self.BASE_DIR, "ogrenci_analiz_modeli.pkl")
        try:
            self.ml_model = joblib.load(pkl_yolu)
            print("✅ [SİSTEM] ML Sınıflandırma Modeli (.pkl) Yüklendi!")
        except Exception as e:
            self.ml_model = None
            print(f"⚠️ HATA: .pkl dosyası bulunamadı! {e}")
        # ----------------------------------------

        model_name = 'deepseek-ai/DeepSeek-OCR-2'
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True, local_files_only=True)

        q_config = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True, bnb_4bit_quant_type="nf4"
        )

        self.ocr_model = AutoModel.from_pretrained(
            model_name, trust_remote_code=True, use_safetensors=True,
            quantization_config=q_config, device_map="cuda",
            torch_dtype=torch.bfloat16, local_files_only=True
        ).eval()
        print("✅ [SİSTEM] DeepSeek OCR Motoru Hazır!\n")

    def kagidi_oku_ve_degerlendir(self, resim_yolu):
        CEVAP_ANAHTARI = {"1": "A", "2": "A", "3": "A", "4": "A", "5": "A"}

        yakalayici = io.StringIO()
        eski_stdout = sys.stdout
        sys.stdout = yakalayici

        try:
            if torch.cuda.is_available(): torch.cuda.empty_cache()
            with torch.no_grad():
                with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                    if hasattr(self.ocr_model, "generation_config"):
                        self.ocr_model.generation_config.max_new_tokens = 2048

                    prompt_metni = "<image>\n<|grounding|>Convert the document to markdown."
                    
                    # Model return vermiyor, doğrudan sys.stdout'a yazıyor
                    self.ocr_model.infer(
                        self.tokenizer, prompt=prompt_metni, image_file=resim_yolu,
                        output_path="./", base_size=1024, image_size=768,
                        crop_mode=True, save_results=False
                    )
        except Exception as e:
            eski_stdout.write(f"\n⚠️ Hata: {str(e)}\n")
        finally:
            sys.stdout = eski_stdout
            # İşte AI'ın saf çıktısı burada!
            raw_output = yakalayici.getvalue() 

        okunan_veriler = {"sinav_id": "00000", "ogrenci_no": "0000", "sorular": {}, "toplam_puan": 0}

        # --- 1. ID YAKALAMA (Kelimeye bakmaksızın 4 ve 5 haneli sayıları bulur) ---
        s_id_match = re.search(r'\b(\d{5})\b', raw_output)
        if s_id_match: okunan_veriler["sinav_id"] = s_id_match.group(1)

        o_no_match = re.findall(r'\b(\d{4})\b', raw_output)
        for m in o_no_match:
            if m not in ['1024', '1280', '2048']: # Sistem loglarını es geç
                okunan_veriler["ogrenci_no"] = m
                break

        # --- 2. HTML TABLO ANALİZİ (Puan tabloları için Mükemmel Çözüm) ---
        table_match = re.search(r'<table>.*?</table>', raw_output, re.DOTALL | re.IGNORECASE)
        if table_match:
            rows = re.findall(r'<tr>(.*?)</tr>', table_match.group(), re.IGNORECASE | re.DOTALL)
            if len(rows) >= 2:
                # HTML etiketlerini silip sadece hücreleri alıyoruz
                headers = [re.sub(r'<[^>]+>', '', td).strip().upper() for td in re.findall(r'<td>(.*?)</td>', rows[0], re.IGNORECASE)]
                values = [re.sub(r'<[^>]+>', '', td).strip().upper() for td in re.findall(r'<td>(.*?)</td>', rows[1], re.IGNORECASE)]
                
                # S1, S2 vs ile Puanları Eşleştir
                for h, v in zip(headers, values):
                    q_match = re.search(r'S(?:ORU)?\s*(\d)', h)
                    if q_match:
                        q_num = q_match.group(1)
                        if v in ["A", "B", "C", "D", "E"]:
                            okunan_veriler["sorular"][q_num] = 20 if v == CEVAP_ANAHTARI.get(q_num) else 0
                        elif v.isdigit():
                            okunan_veriler["sorular"][q_num] = int(v) if int(v) <= 100 else 0

        # --- 3. YEDEK: OPTİK FORM VEYA LİSTE FORMATI ---
        if len(okunan_veriler["sorular"]) < 5:
            clean_text = re.sub(r'<[^>]+>', ' ', raw_output) # HTML'leri temizle
            # 1. A, 1) B, S1: 20 gibi formatları yakala
            for m in re.finditer(r'\b([1-5])\s*[\.\):\s-]+\s*([A-E]|\d{1,3})\b', clean_text, re.IGNORECASE):
                q_num, val = m.group(1), m.group(2).upper()
                if str(q_num) not in okunan_veriler["sorular"]:
                    if val in ["A", "B", "C", "D", "E"]:
                        okunan_veriler["sorular"][q_num] = 20 if val == CEVAP_ANAHTARI.get(q_num) else 0
                    elif val.isdigit():
                        okunan_veriler["sorular"][q_num] = int(val) if int(val) <= 100 else 0

        # Okunamayan sorulara 0 bas
        for i in range(1, 6):
            if str(i) not in okunan_veriler["sorular"]:
                okunan_veriler["sorular"][str(i)] = 0

        # Son Karar
        okunan_veriler["toplam_puan"] = sum(okunan_veriler["sorular"].values())
        okunan_veriler["yapay_zeka_karari"] = "Geçti" if okunan_veriler["toplam_puan"] >= 50 else "Kaldı"
        okunan_veriler["toplam_puan"] = sum(okunan_veriler["sorular"].values())
        
        # ML MODELİ İLE GEÇTİ/KALDI TAHMİNİ
        try:
            import pandas as pd
            ML_beklenen_sutunlar = ['soru_1', 'soru_2', 'soru_3', 'soru_4', 'soru_5']
            # Soruların notlarını bir diziye alıyoruz
            ml_input = [okunan_veriler["sorular"].get(str(i), 0) for i in range(1, 6)]
            
            # DataFrame formatına çevirip modele soruyoruz
            input_df = pd.DataFrame([ml_input], columns=ML_beklenen_sutunlar)
            tahmin = self.ml_model.predict(input_df)[0]
            
            # Model 1 (Geçti) veya 0 (Kaldı) döndürüyor
            okunan_veriler["yapay_zeka_karari"] = "Geçti" if tahmin == 1 else "Kaldı"
        except Exception as e:
            # Eğer .pkl dosyası bulunamazsa veya patlarsa yedek kural devreye girsin
            print(f"⚠️ ML Modeli Çalışmadı (Yedek Kural Devrede): {str(e)}")
            okunan_veriler["yapay_zeka_karari"] = "Geçti" if okunan_veriler["toplam_puan"] >= 50 else "Kaldı"
            
        okunan_veriler["durum"] = "basarili" if okunan_veriler["sinav_id"] != "00000" else "hata"

        return okunan_veriler

    def pdf_isle(self, pdf_yolu):
        """
        Bir PDF dosyasını alır, her sayfasını geçici bir JPEG'e dönüştürür,
        kagidi_oku_ve_degerlendir() ile değerlendirir ve sonuçları liste olarak döndürür.
        Her sayfa CSV'de ayrı bir satır (öğrenci/sınav kağıdı) olarak temsil edilir.
        """
        if not PYMUPDF_MEVCUT:
            print("❌ [HATA] PyMuPDF yüklü değil, PDF işlenemiyor.")
            return []

        sonuclar = []
        try:
            belge = fitz.open(pdf_yolu)
            print(f"📄 [PDF] '{os.path.basename(pdf_yolu)}' açıldı — {len(belge)} sayfa bulundu.")
        except Exception as e:
            print(f"❌ [HATA] PDF açılamadı: {e}")
            return []

        for sayfa_no in range(len(belge)):
            gecici_dosya = None
            try:
                sayfa = belge[sayfa_no]
                # 2x zoom → ~150 DPI (okunabilir kalite)
                matris = fitz.Matrix(2, 2)
                piksel = sayfa.get_pixmap(matrix=matris)

                # Geçici JPEG dosyası oluştur
                with tempfile.NamedTemporaryFile(
                    suffix=".jpg", prefix=f"pdf_sayfa_{sayfa_no + 1}_", delete=False
                ) as tmp:
                    gecici_dosya = tmp.name

                piksel.save(gecici_dosya)
                print(f"  🖼️  Sayfa {sayfa_no + 1} geçici dosyaya yazıldı: {gecici_dosya}")

                # Mevcut OCR motoruna gönder
                sonuc = self.kagidi_oku_ve_degerlendir(gecici_dosya)
                sonuc["kaynak_dosya"] = os.path.basename(pdf_yolu)
                sonuc["pdf_sayfa_no"] = sayfa_no + 1
                sonuclar.append(sonuc)
                print(f"  ✅ Sayfa {sayfa_no + 1} değerlendirildi — Puan: {sonuc['toplam_puan']}")

            except Exception as e:
                print(f"  ⚠️ Sayfa {sayfa_no + 1} işlenirken hata: {e}")
            finally:
                # Geçici resmi her koşulda sil
                if gecici_dosya and os.path.exists(gecici_dosya):
                    try:
                        os.remove(gecici_dosya)
                        print(f"  🗑️  Geçici dosya silindi: {gecici_dosya}")
                    except Exception as e:
                        print(f"  ⚠️ Geçici dosya silinemedi: {e}")

        belge.close()
        print(f"✅ [PDF] '{os.path.basename(pdf_yolu)}' tamamlandı — {len(sonuclar)} sayfa işlendi.")
        return sonuclar


def dosyayi_isle(motor, dosya_yolu):
    """
    Dosya uzantısına göre yönlendirme yapar:
    - .jpg / .jpeg → mevcut tekli OCR akışı (liste içinde tek eleman döner)
    - .pdf         → PDF'in her sayfası ayrı bir sonuç olarak döner
    Dönen değer her zaman dict listesidir; CSV'ye doğrudan satır olarak yazılabilir.
    """
    uzanti = os.path.splitext(dosya_yolu)[1].lower()
    if uzanti in (".jpg", ".jpeg", ".png"):
        sonuc = motor.kagidi_oku_ve_degerlendir(dosya_yolu)
        sonuc.setdefault("kaynak_dosya", os.path.basename(dosya_yolu))
        sonuc.setdefault("pdf_sayfa_no", None)
        return [sonuc]
    elif uzanti == ".pdf":
        return motor.pdf_isle(dosya_yolu)
    else:
        print(f"⚠️ Desteklenmeyen dosya tipi: {uzanti}")
        return []