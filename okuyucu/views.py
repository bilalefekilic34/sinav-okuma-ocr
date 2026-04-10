from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.db.models import Avg, Count, Q  # İstatistikler için eklendi!
import os
from .models import SinavSonucu, Ogrenci, Sinav, Ders

def ana_sayfa(request):
    sinav_id = request.GET.get('sinav_id')
    ogrenci_no = request.GET.get('ogrenci_no')
    
    sonuclar = None
    baslik = ""
    sorgu_tipi = ""
    
    # İstatistik değişkenlerini varsayılan olarak sıfırlıyoruz
    ortalama = 0
    gecen_sayisi = 0
    kalan_sayisi = 0

    # 1. SENARYO: Sınav ID ile arama
    if sinav_id:
        sonuclar = SinavSonucu.objects.filter(sinav_id=sinav_id).select_related('ogrenci', 'sinav__ders')
        baslik = f"Sınav Sonuçları: {sinav_id}"
        sorgu_tipi = "sinav"
        
        # --- İSTATİSTİK MOTORU (Sadece Sınav aramasında çalışır) ---
        if sonuclar.exists():
            istatistikler = sonuclar.aggregate(
                ortalama_puan=Avg('toplam_puan'),
                gecen_sayisi=Count('id', filter=Q(ai_karari='Geçti')),
                kalan_sayisi=Count('id', filter=Q(ai_karari='Kaldı'))
            )
            # Eğer ortalama None dönerse (sıfıra bölünme hatası olmasın diye) 0 yapıyoruz
            ham_ortalama = istatistikler['ortalama_puan'] if istatistikler['ortalama_puan'] is not None else 0
            ortalama = round(ham_ortalama, 2)
            gecen_sayisi = istatistikler['gecen_sayisi']
            kalan_sayisi = istatistikler['kalan_sayisi']
        
    # 2. SENARYO: Öğrenci No ile arama
    elif ogrenci_no:
        sonuclar = SinavSonucu.objects.filter(ogrenci_id=ogrenci_no).select_related('sinav', 'sinav__ders')
        baslik = f"Öğrenci Karnesi: {ogrenci_no}"
        sorgu_tipi = "ogrenci"

    # Eğer bir arama yapıldıysa sonuç sayfasına, yapılmadıysa ana sayfaya yolla
    if sonuclar is not None:
        context = {
            'sonuclar': sonuclar,
            'baslik': baslik,
            'sorgu_tipi': sorgu_tipi,
            'arama_param': sinav_id if sinav_id else ogrenci_no,
            # İstatistikleri şablona gönderiyoruz
            'ortalama': ortalama,
            'gecen_sayisi': gecen_sayisi,
            'kalan_sayisi': kalan_sayisi
        }
        return render(request, 'sonuclar.html', context)

    return render(request, 'index.html')

@csrf_exempt 
def sinav_yukle_api(request):
    from .ai_engine import SinavMotoru 
    motor = SinavMotoru()

    if request.method == 'POST' and request.FILES.get('sinav_kagidi'):
        yuklenen_kagit = request.FILES['sinav_kagidi']
        
        gecici_yol = f"temp_{yuklenen_kagit.name}"
        with open(gecici_yol, 'wb+') as hedef:
            for chunk in yuklenen_kagit.chunks():
                hedef.write(chunk)
                
        sonuclar = motor.kagidi_oku_ve_degerlendir(gecici_yol)
        
        if os.path.exists(gecici_yol):
            os.remove(gecici_yol)
            
        if sonuclar.get("durum") == "basarili":
            s_id = str(sonuclar.get("sinav_id", ""))
            o_no = str(sonuclar.get("ogrenci_no", ""))
            
            print(f"DEBUG: Okunan ID: {s_id}, Okunan No: {o_no}")

            if s_id == "" or o_no == "":
                return JsonResponse({"durum": "hata", "mesaj": f"Eksik Veri! ID:{s_id} No:{o_no}. Lütfen kağıdı ortalayın."})

            ders, _ = Ders.objects.get_or_create(ders_id="BLG101", defaults={"ders_adi": "Otomatik Eklenen Ders"})
            sinav, _ = Sinav.objects.get_or_create(sinav_id=s_id, defaults={"ders": ders, "sinav_adi": "Tarandı"})
            ogrenci, _ = Ogrenci.objects.get_or_create(ogrenci_id=o_no, defaults={"ad_soyad": f"Öğrenci {o_no}"})
            
            SinavSonucu.objects.update_or_create(
                ogrenci=ogrenci,
                sinav=sinav,
                defaults={
                    "soru_1": sonuclar.get("soru_1", 0),
                    "soru_2": sonuclar.get("soru_2", 0),
                    "soru_3": sonuclar.get("soru_3", 0),
                    "soru_4": sonuclar.get("soru_4", 0),
                    "soru_5": sonuclar.get("soru_5", 0),
                    "toplam_puan": sonuclar.get("toplam_puan", 0),
                    "ai_karari": sonuclar.get("yapay_zeka_karari", "Bilinmiyor")
                }
            )
            
        return JsonResponse(sonuclar)
    
    return JsonResponse({"durum": "hata", "mesaj": "Sadece POST isteği ve 'sinav_kagidi' dosyası kabul edilir."})