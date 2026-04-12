import random
from faker import Faker
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from okuyucu.models import Ders, Ogrenci, Sinav, SinavSonucu, Akademisyen

class Command(BaseCommand):
    help = 'Sisteme test etmek için sahte veriler (dummy data) ekler'

    def handle(self, *args, **kwargs):
        fake = Faker('tr_TR')  # Türkçe isimler üretmesi için
        
        self.stdout.write(self.style.SUCCESS('🗑️  Veritabanı temizleniyor... (Superuser/Admin hariç)'))
        
        # Superuser HARİÇ eski çalışan verilerini temizliyoruz
        User.objects.filter(is_superuser=False).delete()
        Akademisyen.objects.all().delete()
        Ders.objects.all().delete()
        Ogrenci.objects.all().delete()
        Sinav.objects.all().delete()
        SinavSonucu.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS('📚 1. Dersler Ekleniyor (20 Adet)...'))
        dersler = []
        ders_kodlari = ["BIL", "MAT", "FIZ", "KIM", "MYS", "YAZ", "CST", "ELK"]
        for i in range(20):
            d_kod = f"{random.choice(ders_kodlari)}{random.randint(101, 499)}-{i}"
            ders = Ders.objects.create(
                ders_id=d_kod,
                ders_adi=fake.job() + " Uygulamaları"
            )
            dersler.append(ders)
            
        self.stdout.write(self.style.SUCCESS('🎓 2. Öğrenciler Ekleniyor (50 Adet)...'))
        ogrenciler = []
        for i in range(50):
            ogrenci = Ogrenci.objects.create(
                ogrenci_id=str(4000 + i),
                ad_soyad=fake.name()
            )
            ogrenciler.append(ogrenci)
            
        self.stdout.write(self.style.SUCCESS('👨‍🏫 3. Akademisyenler Ekleniyor (10 Adet)...'))
        akademisyenler = []
        unvanlar = ["Prof. Dr.", "Doç. Dr.", "Dr. Öğr. Üyesi", "Arş. Gör.", "Öğr. Gör."]
        for i in range(10):
            username = f"hoca{i+1}"
            email = fake.email()
            ad_soyad = fake.name()
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password="password",
                first_name=ad_soyad.split()[0],
                last_name=" ".join(ad_soyad.split()[1:])
            )
            
            akad = Akademisyen.objects.create(
                user=user,
                akademisyen_id=f"A{1000 + i}"
            )
            
            # Rastgele ders ataması (2-4 arası)
            atanacak_dersler = random.sample(dersler, random.randint(2, 4))
            akad.verdigi_dersler.set(atanacak_dersler)
            
            akademisyenler.append(akad)
            
        self.stdout.write(self.style.SUCCESS('📝 4. Sınavlar ve Geçmiş Sınav Sonuçları Ekleniyor...'))
        sinav_isimleri = ["Vize", "Final", "Bütünleme", "Ara Sınav 1", "Ara Sınav 2"]
        ai_kararlari = ["Geçti", "Geçti", "Geçti", "Kaldı"] 
        
        sinav_counter = 1
        for ders in dersler:
            for i in range(random.randint(1, 2)):
                sinav = Sinav.objects.create(
                    sinav_id=str(10000 + sinav_counter),
                    ders=ders,
                    sinav_adi=f"2026 {random.choice(sinav_isimleri)}"
                )
                sinav_counter += 1
                
                # Bu sınava rastgele öğrenciler girecek (10-25 arası)
                sinava_girenler = random.sample(ogrenciler, random.randint(10, 25))
                # Dersi veren hocalardan birini bulalım
                dersin_hocalari = list(ders.akademisyenler.all())
                sorumlu_hoca = random.choice(dersin_hocalari) if dersin_hocalari else None
                
                for ogr in sinava_girenler:
                    # Dinamik JSON puanları (3 ile 7 soru arası)
                    soru_sayisi = random.randint(3, 7)
                    sorular_dict = {}
                    toplam_p = 0
                    for q in range(1, soru_sayisi + 1):
                        puan = random.randint(10, 25) 
                        sorular_dict[str(q)] = puan
                        toplam_p += puan
                        
                    ai_k = "Geçti" if toplam_p >= 50 else random.choice(ai_kararlari)
                        
                    SinavSonucu.objects.create(
                        ogrenci=ogr,
                        sinav=sinav,
                        sorular_ve_puanlar=sorular_dict,
                        toplam_puan=toplam_p,
                        ai_karari=ai_k,
                        akademisyen=sorumlu_hoca,
                        onaylandi_mi=True
                    )
                    
        self.stdout.write(self.style.SUCCESS('\\n✅ İŞLEM TAMAMLANDI! Veriler başarıyla tohumlandı (Seeded).'))
        self.stdout.write(self.style.WARNING("============================================="))
        self.stdout.write(self.style.WARNING("👨‍💻 Akademisyen Giriş Bilgileri:"))
        for i in range(10):
            self.stdout.write(f"   Kullanıcı Adı: hoca{i+1} | Şifre: password")
        self.stdout.write(self.style.WARNING("============================================="))
