import os
import torch
import joblib
import json
import pandas as pd
import re
import shutil
import time
import sys
import io  # <--- Hatanın çözümü burada!
from transformers import AutoModel, AutoTokenizer, BitsAndBytesConfig

# --- HOCANIN KURALI: İNTERNET BAĞLANTISINI TAMAMEN KES ---
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
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # ML Model Yükleme
        pkl_yolu = os.path.join(self.BASE_DIR, "ogrenci_analiz_modeli.pkl") 
        self.ml_model = joblib.load(pkl_yolu)
        
        # DeepSeek Model Yükleme
        model_name = 'deepseek-ai/DeepSeek-OCR-2'
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True, local_files_only=True)
        
        q_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )
        
        self.ocr_model = AutoModel.from_pretrained(
            model_name, trust_remote_code=True, use_safetensors=True,
            quantization_config=q_config, device_map="cuda",
            torch_dtype=torch.bfloat16, local_files_only=True 
        ).eval()
        print("✅ [SİSTEM] Tüm Motorlar OFFLINE Olarak Göreve Hazır!\n")

    def kagidi_oku_ve_degerlendir(self, resim_yolu):
        from .models import SinavSonucu 
        import io, sys, re, json, os, pandas as pd, shutil, time

        # 1. KAPAN VE TEMİZLİK
        yakalayici = io.StringIO()
        eski_stdout = sys.stdout
        sys.stdout = yakalayici
        
        raw_output = ""
        try:
            # ÖNEMLİ: Ardışık okumalarda RAM şişmesini önle
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            with torch.no_grad():
                with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                    # Kâğıdın yarısında yazının kesilmemesi için maksimum kelime üretim limitini artırıyoruz
                    if hasattr(self.ocr_model, "generation_config"):
                        self.ocr_model.generation_config.max_new_tokens = 2048
                        
                    res = self.ocr_model.infer(
                        self.tokenizer, 
                        prompt="<image>\n<|grounding|>Convert the document to markdown.", 
                        image_file=resim_yolu, 
                        output_path="./", 
                        base_size=1024, image_size=768, 
                        crop_mode=True, 
                        save_results=False
                    )
                    if res: raw_output = str(res)
        except Exception as e:
            eski_stdout.write(f"\n⚠️ OCR Hatası: {str(e)}\n")
            print(f">>> MODEL ÇÖKTÜ VEYA OOM: {str(e)}") # Konsoldan hemen görelim
        finally:
            sys.stdout = eski_stdout
            # Terminalden ve return'den gelen her şeyi topla
            raw_output += "\n" + yakalayici.getvalue()

        # 2. TEMİZLİK: Teknik logları (torch.Size, 1280 vs.) metinden siliyoruz
        # Önce torch loglarını temizle
        temiz_metin = re.sub(r'torch\.Size\(\[.*?\]\)', '', raw_output)
        # 1280, 1024 gibi teknik rakamlar eğer "Size" veya "BASE" gibi kelimelerin yanındaysa sil
        temiz_metin = re.sub(r'(?:BASE|PATCHES|Size|torch)[:\s\[]*\d+', '', temiz_metin, flags=re.IGNORECASE)
        # Bounding box koordinatlarını ( [[180, 160, 279, 185]] gibi ) metinden kaldır ki sayılarla karışmasın
        temiz_metin = re.sub(r'\[\[.*?\]\]', ' ', temiz_metin)
        # HTML tagları geldiyse (<table... <td> vs), dümdüz metne çevir ki sayılar okunsun
        temiz_metin = re.sub(r'<[^>]+>', ' ', temiz_metin)

        print(f"\n--- [DEBUG] TEMİZLENMİŞ HAM VERİ ---\n{temiz_metin}\n---------------------------")

        okunan_veriler = {
            "sinav_id": "00000", "ogrenci_no": "0000",
            "soru_1": -1, "soru_2": -1, "soru_3": -1, "soru_4": -1, "soru_5": -1
        }

        # JSON Çıkarımı: Öncelikle metin içinde ```json ... ``` bloğunu arıyoruz
        json_match = re.search(r'```json\s*(.*?)\s*```', temiz_metin, re.DOTALL)
        if not json_match:
            # Sadece { ... } kısmını arayabiliriz
            json_match = re.search(r'\{[^{}]*\}', temiz_metin, re.DOTALL)

        if json_match:
            try:
                parsed_json = json.loads(json_match.group(1) if '```' in json_match.group(0) else json_match.group(0))
                okunan_veriler["sinav_id"] = str(parsed_json.get("sinav_id", "00000"))
                okunan_veriler["ogrenci_no"] = str(parsed_json.get("ogrenci_no", "0000"))
                for i in range(1, 6):
                    okunan_veriler[f"soru_{i}"] = int(parsed_json.get(f"soru_{i}", -1))
            except Exception as e:
                print(f"JSON Parse Hatası: {e}")

        # Eğer hala 00000 / 0000 var ise Regex ile klasik yöntem (ama daha zeki)
        if okunan_veriler["sinav_id"] == "00000" or okunan_veriler["ogrenci_no"] == "0000":
            # Tablo çizgilerini (|) ve boşlukları destekleyecek şekle getirildi
            s_id_match = re.search(r'(?:Sinav|Exam|ID)[\s:\|]*(\d{5})', temiz_metin, re.IGNORECASE)
            o_no_match = re.search(r'(?:Ogr|Org|Student|No)[\s:\|]*(\d{4})', temiz_metin, re.IGNORECASE)
            if s_id_match: okunan_veriler["sinav_id"] = s_id_match.group(1)
            if o_no_match: okunan_veriler["ogrenci_no"] = o_no_match.group(1)

        # ID'ler için sayı uzunluk tabanlı en son çare (Güvenilir değil, ama loglara karşı korumalı)
        if okunan_veriler["sinav_id"] == "00000":
            for s in re.findall(r'\b\d{5}\b', temiz_metin):
                okunan_veriler["sinav_id"] = s
                break
                
        if okunan_veriler["ogrenci_no"] == "0000":
            for s in re.findall(r'\b\d{4}\b', temiz_metin):
                # 1024, 1280 vs modelin sızdırdığı teknik logları kesinlikle yoksay
                if s not in ['1024', '1280', '2048']:
                    okunan_veriler["ogrenci_no"] = s
                    break

        # PUANLARI ARAMA MANTIĞI:
        
        # 1. Aşama: Tam etiketler (Soru 1, S1, Soru01) (Markdown tablolarını | operatörü ile kapsar)
        for i in range(1, 6):
            # '-', sınıfın en sonuna kondu ki aralık (.dan :ye gibi) yaratmasın!
            soru_match = re.search(rf'(?:Soru\s*{i}|S\s*{i}|Soru0?{i})[\s:\|]+(\d+)', temiz_metin, re.IGNORECASE)
            if soru_match:
                okunan_veriler[f"soru_{i}"] = int(soru_match.group(1))
        print(f">>> [AŞAMA 1 BİTİMİ] { [okunan_veriler[f'soru_{i}'] for i in range(1,6)] }")
                
        # 2. Aşama: Puanlı ve az noktalı liste formatı (1. 20, 1) 15, 1: 10, | 1 | 20 vb)
        for i in range(1, 6):
            if okunan_veriler[f"soru_{i}"] == -1:
                # '-', sınıfın en sonuna kondu ki aralık yaratmasın!
                isaretli_match = re.search(rf'\b{i}\s*[\.\):\|]+(?:\s|-)*(\d+)', temiz_metin)
                if isaretli_match:
                    okunan_veriler[f"soru_{i}"] = int(isaretli_match.group(1))
        print(f">>> [AŞAMA 2 BİTİMİ] { [okunan_veriler[f'soru_{i}'] for i in range(1,6)] }")

        # Hala -1 olan puanlar var mı?
        eksik_var = any(okunan_veriler[f"soru_{i}"] == -1 for i in range(1, 6))

        # 3. Aşama: "PUAN" veya "PUANLAR" başlığı altındaki liste
        if eksik_var and "PUAN" in temiz_metin.upper():
            puan_kismi = temiz_metin.upper().split("PUAN")[-1]
            puanlar = re.findall(r'\b\d+\b', puan_kismi)
            toplanan = [int(p) for p in puanlar if int(p) <= 100]
            print(f">>> [AŞAMA 3] 'PUAN' bulundu. Toplanan: {toplanan}")
            # Zaten bulduklarımızı ezmeden kalanı ekle
            idx = 0
            for i in range(1, 6):
                if okunan_veriler[f"soru_{i}"] == -1 and idx < len(toplanan):
                    okunan_veriler[f"soru_{i}"] = toplanan[idx]
                    idx += 1
            eksik_var = any(okunan_veriler[f"soru_{i}"] == -1 for i in range(1, 6))
        print(f">>> [AŞAMA 3 BİTİMİ] { [okunan_veriler[f'soru_{i}'] for i in range(1,6)] }")

        # 4. Aşama: Hiçbir format kalmadıysa, serbest sayı dizisine bak (Örn: 1 20 2 15 3 0 4 5 5 10 veya dümdüz 20 15 0 5 10)
        if eksik_var:
            # ID ve NO'yu karıştırmamak için sil
            sade_metin = temiz_metin
            if okunan_veriler["sinav_id"] != "00000": sade_metin = sade_metin.replace(okunan_veriler["sinav_id"], " ")
            if okunan_veriler["ogrenci_no"] != "0000": sade_metin = sade_metin.replace(okunan_veriler["ogrenci_no"], " ")
            
            _tum = [int(x) for x in re.findall(r'\b\d+\b', sade_metin) if int(x) <= 100]
            # Form: 1 X 2 Y 3 Z 4 W 5 V mi?
            # 1, 2, 3, 4, 5 listesinin elemanlarını sırayla içeriyor mu? Ve sayıları tamamsa:
            hedef_soru = 1
            puan_adaylari = []
            for num in _tum:
                if num == hedef_soru:
                    hedef_soru += 1
                else:
                    # Soru numarası değilse puandır
                    puan_adaylari.append(num)
            
            if hedef_soru > 5 and len(puan_adaylari) >= 5:
                # Muhtemelen sayılarıyla beraber Soru1, Puan1 diye aktı
                pass # puan_adaylari listesini sırayla kullanacagiz
            else:
                # Direkt dümdüz puanlar
                # Ama ilk baştaki gereksiz 1, 2, 3 ler varsa? (sadece puan listesiyse sorun yok)
                # Yine sadece eksikleri doldur, 1-5 fırça silmesi (silersen sıfır alan da yanar) yapmak tehlikeli.
                puan_adaylari = _tum

            idx = 0
            for i in range(1, 6):
                if okunan_veriler[f"soru_{i}"] == -1 and idx < len(puan_adaylari):
                    okunan_veriler[f"soru_{i}"] = puan_adaylari[idx]
                    idx += 1
        print(f">>> [AŞAMA 4 BİTİMİ] { [okunan_veriler[f'soru_{i}'] for i in range(1,6)] }")

        # Güvenlik: Maksimum soru puanı muhtemelen 100'ü geçemez. Ayrıca -1 kalanları 0'a çek
        for i in range(1, 6):
            if okunan_veriler[f"soru_{i}"] > 100 or okunan_veriler[f"soru_{i}"] == -1:
                okunan_veriler[f"soru_{i}"] = 0

        # Toplam ve ML Tahmini
        okunan_veriler["toplam_puan"] = sum([okunan_veriler[f"soru_{i}"] for i in range(1, 6)])
        
        input_df = pd.DataFrame([[okunan_veriler["soru_1"], okunan_veriler["soru_2"], okunan_veriler["soru_3"], okunan_veriler["soru_4"], okunan_veriler["soru_5"]]], columns=['soru_1', 'soru_2', 'soru_3', 'soru_4', 'soru_5'])
        tahmin = self.ml_model.predict(input_df)[0]
        okunan_veriler["yapay_zeka_karari"] = "Geçti" if tahmin == 1 else "Kaldı"
        okunan_veriler["durum"] = "basarili" if okunan_veriler["sinav_id"] != "00000" else "hata"
        
        return okunan_veriler