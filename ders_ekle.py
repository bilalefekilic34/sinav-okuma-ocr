import random
from okuyucu.models import Ders, Ogrenci

def sistemi_canlandir():
    # 1. Yeni dersleri ekle
    yeni_dersler = {
        "12077": "Lineer Cebir",
        "32041": "Makine Öğrenmesi",
        "87039": "Genel Kimya",
        "52011": "İşletim Sistemleri"
    }
    
    for d_id, d_ad in yeni_dersler.items():
        Ders.objects.get_or_create(ders_id=d_id, defaults={'ders_adi': d_ad})
    
    # 2. Tüm dersleri listele
    tum_dersler = list(Ders.objects.all())
    
    # 3. Her öğrenciye tam 3 ders ata
    ogrenciler = Ogrenci.objects.all()
    for ogrenci in ogrenciler:
        # Rastgele 3 ders seç
        secilenler = random.sample(tum_dersler, 3)
        ogrenci.kayitli_dersler.set(secilenler)
        ogrenci.save()
    
    print(f"İşlem tamam: 4 ders eklendi ve {ogrenciler.count()} öğrenciye 3'er ders atandı.")

sistemi_canlandir()