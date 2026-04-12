import os
import csv
import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from okuyucu.models import Ders, Ogrenci, Sinav, SinavSonucu, Akademisyen

class Command(BaseCommand):
    help = 'CSV dosyasından gerçek verilerle veritabanını doldurur.'

    def handle(self, *args, **kwargs):
        # CSV Dosyası manage.py ile ayni klasorde degil, bir ust klasorde (DeepSeek-OCR-2-main dizininde)
        # manage.py dizini: __file__'ın 4 üstü
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        csv_yolu = os.path.join(base_dir, '..', 'makine_ogrenmesi_veriseti.csv')
        csv_yolu = os.path.normpath(csv_yolu)
        
        self.stdout.write(self.style.WARNING('🗑️ Mevcut veriler temizleniyor (Admin haric)...'))
        User.objects.filter(is_superuser=False).delete()
        Akademisyen.objects.all().delete()
        Ders.objects.all().delete()
        Ogrenci.objects.all().delete()
        Sinav.objects.all().delete()
        SinavSonucu.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS('\n👨‍🏫 1. Akademisyenler Olusturuluyor...'))
        akademisyenler = []
        for i in range(101, 111):
            username = f'AKAD{i}'
            user = User.objects.create_user(
                username=username,
                password='123456',
                first_name='Eğitmen',
                last_name=str(i)
            )
            akad = Akademisyen.objects.create(
                user=user,
                akademisyen_id=username
            )
            akademisyenler.append(akad)
            
        self.stdout.write(self.style.SUCCESS('📚 2. Ders Olusturuluyor (Yazılım Mühendisliği)...'))
        ders = Ders.objects.create(ders_id="YAZ101", ders_adi="Yazılım Mühendisliği")
        
        # Tüm hocaları derse ata
        for akad in akademisyenler:
            akad.verdigi_dersler.add(ders)

        self.stdout.write(self.style.SUCCESS(f'📝 3. CSV İşleniyor: {csv_yolu}'))
        
        if not os.path.exists(csv_yolu):
            self.stdout.write(self.style.ERROR(f'HATA: {csv_yolu} bulunamadı! Lütfen dosya yolunu kontrol edin.'))
            return
            
        ogrenci_cache = {}
        sinav_cache = {}
        eklenen_sonuc_sayisi = 0

        with open(csv_yolu, 'r', encoding='utf-8') as f:
            # Sütunlar: dosya_adi, ogrenci_no, sinav_id, soru_1, soru_2, soru_3, soru_4, soru_5, toplam_puan
            reader = csv.DictReader(f)
            
            for row in reader:
                ogrenci_no = str(row['ogrenci_no']).strip()
                sinav_id = str(row['sinav_id']).strip()
                
                if not ogrenci_no or not sinav_id:
                    continue
                    
                # Öğrenci oluştur veya cache'ten al
                if ogrenci_no not in ogrenci_cache:
                    ogrenci = Ogrenci.objects.create(ogrenci_id=ogrenci_no, ad_soyad=f"Öğrenci {ogrenci_no}")
                    ogrenci_cache[ogrenci_no] = ogrenci
                else:
                    ogrenci = ogrenci_cache[ogrenci_no]
                    
                # Sınav oluştur veya cache'ten al
                if sinav_id not in sinav_cache:
                    sinav = Sinav.objects.create(sinav_id=sinav_id, ders=ders, sinav_adi="Dönem Sonu Sınavı")
                    sinav_cache[sinav_id] = sinav
                else:
                    sinav = sinav_cache[sinav_id]
                
                # Dinamik JSON formatı: Dinamik Puanlar
                sorular_dict = {
                    "1": int(row.get('soru_1', 0)),
                    "2": int(row.get('soru_2', 0)),
                    "3": int(row.get('soru_3', 0)),
                    "4": int(row.get('soru_4', 0)),
                    "5": int(row.get('soru_5', 0)),
                }
                
                toplam_puan = int(row.get('toplam_puan', 0))
                ai_k = "Geçti" if toplam_puan >= 50 else "Kaldı"
                sorumlu_hoca = random.choice(akademisyenler)
                
                SinavSonucu.objects.update_or_create(
                    ogrenci=ogrenci,
                    sinav=sinav,
                    defaults={
                        "sorular_ve_puanlar": sorular_dict,
                        "toplam_puan": toplam_puan,
                        "ai_karari": ai_k,
                        "akademisyen": sorumlu_hoca,
                        "onaylandi_mi": True
                    }
                )
                eklenen_sonuc_sayisi += 1

        self.stdout.write(self.style.SUCCESS(f'\n✅ İŞLEM TAMAMLANDI! (Toplam {eklenen_sonuc_sayisi} form içeri aktarıldı)'))
        self.stdout.write(self.style.WARNING("============================================="))
        self.stdout.write(self.style.WARNING("👨‍💻 Akademisyen Giriş Bilgileri:"))
        self.stdout.write("   Kullanıcı Adı: AKAD101 ... AKAD110")
        self.stdout.write("   Şifre: 123456")
        self.stdout.write(self.style.WARNING("============================================="))
