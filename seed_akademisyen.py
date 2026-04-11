import os
import django
import random

# 1. Django ayarlarını yükle
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sinav_sistemi.settings') # Proje adın farklıysa düzelt
django.setup()

from okuyucu.models import Akademisyen, Ders

def veri_uret():
    print("🚀 Sentetik veri operasyonu başladı...")
    
    # Mevcut dersleri çekelim
    tum_dersler = list(Ders.objects.all())
    
    if not tum_dersler:
        print("❌ Hata: Veritabanında hiç ders yok! Önce ders eklemelisin.")
        return

    # Sıkacağımız akademisyen dataları
    akademisyen_listesi = [
        {"id": "AKAD101"},
        {"id": "AKAD202"},
        {"id": "AKAD303"},
        {"id": "AKAD404"}
    ]

    for veri in akademisyen_listesi:
        # Akademisyeni oluştur (varsa güncellemez, yoksa oluşturur)
        akad, created = Akademisyen.objects.get_or_create(
            akademisyen_id=veri["id"]
        )
        
        if created:
            # Rastgele 1 ile 3 arasında ders seçip bağlayalım
            secilen_dersler = random.sample(tum_dersler, k=min(len(tum_dersler), random.randint(1, 3)))
            akad.verdigi_dersler.set(secilen_dersler) # ManyToMany bağlantısı
            
            ders_kodlari = [d.ders_id for d in secilen_dersler]
            print(f"✅ {akad.akademisyen_id} oluşturuldu. Bağlanan dersler: {ders_kodlari}")
        else:
            print(f"⚠️ {akad.akademisyen_id} zaten mevcut, atlanıyor.")

    print("\n✨ Operasyon tamamlandı. Akademisyenler derslerine kavuştu.")

if __name__ == "__main__":
    veri_uret()