from django.db import models
from django.contrib.auth.models import User

class Ogrenci(models.Model):
    # Öğrenci No senin sisteminde 4 haneli (Örn: 4021), bunu PK yapıyoruz.
    ogrenci_id = models.CharField(max_length=4, primary_key=True, verbose_name="Öğrenci No")
    ad_soyad = models.CharField(max_length=100, verbose_name="Ad Soyad")
    kayitli_dersler = models.ManyToManyField('Ders', related_name='ogrenciler', blank=True)
    def __str__(self):
        return f"{self.ogrenci_id} - {self.ad_soyad}"

class Ders(models.Model):
    ders_id = models.CharField(max_length=10, primary_key=True, verbose_name="Ders Kodu")
    ders_adi = models.CharField(max_length=100, verbose_name="Ders Adı")

    def __str__(self):
        return self.ders_adi

class Sinav(models.Model):
    # Sınav ID 5 haneli (Örn: 84717)
    sinav_id = models.CharField(max_length=5, primary_key=True, verbose_name="Sınav ID")
    # Bu sınav hangi derse ait? (Ders silinirse sınavlar da silinsin: CASCADE)
    ders = models.ForeignKey(Ders, on_delete=models.CASCADE, related_name="sinavlar")
    sinav_adi = models.CharField(max_length=50, verbose_name="Sınav Adı (Vize/Final)")

    def __str__(self):
        return f"{self.sinav_id} - {self.sinav_adi} ({self.ders.ders_adi})"

class SinavSonucu(models.Model):
    # Bu tablo Öğrenci ve Sınav'ı birleştiren 'Köprü' tablodur.
    ogrenci = models.ForeignKey(Ogrenci, on_delete=models.CASCADE, related_name="sonuclar")
    sinav = models.ForeignKey(Sinav, on_delete=models.CASCADE, related_name="ogrenci_sonuclari")
    
    # Dinamik Soru-Puan Yapısı
    sorular_ve_puanlar = models.JSONField(default=dict, verbose_name="Sorular ve Puanlar")
    toplam_puan = models.IntegerField(default=0)
    
    # Yapay Zeka kararını burada tutuyoruz
    ai_karari = models.CharField(max_length=10, verbose_name="Yapay Zeka Kararı")
    okunma_tarihi = models.DateTimeField(auto_now_add=True)
    akademisyen = models.ForeignKey('Akademisyen', on_delete=models.SET_NULL, null=True, blank=True)
    onaylandi_mi = models.BooleanField(default=False, verbose_name="Onaylandı mı?")
    
    class Meta:
        # Bir öğrencinin aynı sınavda birden fazla sonucu olmasın (Güvenlik kilidi)
        unique_together = ('ogrenci', 'sinav')

    def __str__(self):
        return f"{self.ogrenci.ogrenci_id} -> {self.sinav.sinav_id}: {self.toplam_puan}"

class Akademisyen(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name="akademisyen_profili")
    akademisyen_id = models.CharField(max_length=20, unique=True, verbose_name="Akademisyen ID")
    
    # Bir akademisyen birden fazla ders verebilir
    verdigi_dersler = models.ManyToManyField(
        'Ders', 
        related_name='akademisyenler', 
        blank=True, 
        verbose_name="Verdiği Dersler"
    )

    def __str__(self):
        return str(self.akademisyen_id)
    