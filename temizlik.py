import os
import django
import re
import random

# Proje adın farklıysa 'sinav_sistemi.settings' kısmını kendine göre düzenle
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sinav_sistemi.settings')
django.setup()

from okuyucu.models import Ogrenci, SinavSonucu, Akademisyen

def temizle_ve_ata():
    print("🧹 Çöp veri imha operasyonu başlıyor...")
    
    # 1. TEMİZLİK AŞAMASI
    # Kural: Sadece rakamlardan oluşmalı, tam 4 haneli olmalı VE 0000 OLMAMALI.
    silinen_ogrenci_sayisi = 0
    for ogr in Ogrenci.objects.all():
        # Eğer 4 haneli rakam değilse VEYA 0000 ise UÇUR
        if not re.match(r'^\d{4}$', ogr.ogrenci_id) or ogr.ogrenci_id == "0000":
            ogr.delete() # Öğrenci silinince ona bağlı sınav sonuçları da otomatik uçar (Cascade)
            silinen_ogrenci_sayisi += 1
            
    print(f"✅ Temizlik bitti! {silinen_ogrenci_sayisi} adet çöp kayıt veritabanından kazındı.")

    # 2. AKADEMİSYEN ATAMA AŞAMASI
    print("\n🎲 Rastgele Akademisyen atamaları yapılıyor...")
    akademisyenler = list(Akademisyen.objects.all())
    
    if not akademisyenler:
        print("⚠️ Sistemde hiç Akademisyen yok! Önce akademisyen eklemelisin.")
        return

    atama_sayisi = 0
    # Kalan tertemiz sınav sonuçlarına hoca atıyoruz
    for sonuc in SinavSonucu.objects.all():
        rastgele_hoca = random.choice(akademisyenler)
        sonuc.akademisyen = rastgele_hoca
        sonuc.save()
        atama_sayisi += 1

    print(f"✅ Atama bitti! {atama_sayisi} sınav kağıdına akademisyen mühürü vuruldu.")

if __name__ == "__main__":
    temizle_ve_ata()