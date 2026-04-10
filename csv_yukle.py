import os
import django
import pandas as pd

# 1. Django ortamını bu script için başlatıyoruz (manage.py ile aynı klasörde olmalı)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sinav_sistemi.settings')
django.setup()

# 2. Modellerimizi içeri aktarıyoruz
from okuyucu.models import Ogrenci, Ders, Sinav, SinavSonucu

def verileri_veritabanina_aktar():
    # CSV dosyasının bir üst klasörde (DeepSeek-OCR-2-main içinde) olduğunu varsayıyoruz
    csv_yolu = "../makine_ogrenmesi_veriseti.csv"
    
    if not os.path.exists(csv_yolu):
        print(f"[HATA] CSV dosyası bulunamadı: {csv_yolu}")
        return

    print("CSV dosyası okunuyor...")
    df = pd.read_csv(csv_yolu)

    # 1. Adım: Sisteme sahte bir "Ders" ekle
    ders, created = Ders.objects.get_or_create(
        ders_id="BLG101", 
        defaults={"ders_adi": "Yapay Zekaya Giriş"}
    )
    print("Ders kontrol edildi/oluşturuldu: BLG101")

    # 2. Adım: CSV'deki Sınav ID'sini alıp sisteme "Sınav" olarak ekle
    ornek_sinav_id = str(df.iloc[0]['sinav_id'])
    sinav, created = Sinav.objects.get_or_create(
        sinav_id=ornek_sinav_id, 
        defaults={"ders": ders, "sinav_adi": "Vize Sınavı"}
    )
    print(f"Sınav kontrol edildi/oluşturuldu: {ornek_sinav_id}")

    # 3. Adım: CSV'deki her satırı tek tek Öğrenci ve Sınav Sonucu olarak ekle
    eklenen_kayit = 0
    for index, row in df.iterrows():
        ogrenci_no = str(row['ogrenci_no'])
        
        # Öğrenciyi bul veya oluştur
        ogrenci, _ = Ogrenci.objects.get_or_create(
            ogrenci_id=ogrenci_no, 
            defaults={"ad_soyad": f"Öğrenci {ogrenci_no}"} # Şimdilik isimsiz
        )

        # Yapay zeka kararı simülasyonu (Zaten model de 50'ye göre eğitilmişti)
        ai_karari = "Geçti" if row['toplam_puan'] >= 50 else "Kaldı"

        # Sınav sonucunu köprü tabloya ekle
        SinavSonucu.objects.update_or_create(
            ogrenci=ogrenci,
            sinav=sinav,
            defaults={
                "soru_1": row['soru_1'],
                "soru_2": row['soru_2'],
                "soru_3": row['soru_3'],
                "soru_4": row['soru_4'],
                "soru_5": row['soru_5'],
                "toplam_puan": row['toplam_puan'],
                "ai_karari": ai_karari
            }
        )
        eklenen_kayit += 1

    print(f"\n✅ İŞLEM BAŞARILI! Veritabanına {eklenen_kayit} adet sınav sonucu işlendi.")
    print(f"Test için Ana Sayfaya gidip Sınav ID kısmına '{ornek_sinav_id}' yazabilirsiniz.")

if __name__ == '__main__':
    verileri_veritabanina_aktar()