from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.db.models import Avg, Count, Q  # İstatistikler için eklendi!
import os
from .models import SinavSonucu, Ogrenci, Sinav, Ders, Akademisyen

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
            
# API 2: Tüm Dersleri Listele
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

def api_ogrenciler(request):
    data = list(Ogrenci.objects.values('ogrenci_id', 'ad_soyad'))
    return JsonResponse({'ogrenciler': data})

# API 2: Tüm Dersleri Listele
def api_dersler(request):
    data = list(Ders.objects.values('ders_id', 'ders_adi'))
    return JsonResponse({'dersler': data})

# API 3: Tüm Sınavları Listele
def api_sinavlar(request):
    data = list(Sinav.objects.values('sinav_id', 'sinav_adi', 'ders__ders_id'))
    return JsonResponse({'sinavlar': data})

# API 4: Tüm Akademisyenleri Listele
def api_akademisyenler(request):
    data = list(Akademisyen.objects.values('akademisyen_id'))
    return JsonResponse({'akademisyenler': data})

# API 5: Sistemdeki Tüm Sınav Sonuçları
def api_sonuclar(request):
    data = list(SinavSonucu.objects.values('ogrenci__ogrenci_id', 'sinav__sinav_id', 'toplam_puan', 'ai_karari'))
    return JsonResponse({'sonuclar': data})

# API 6: Spesifik Öğrencinin Karnesi (Dinamik Parametreli)
def api_ogrenci_detay(request, ogrenci_id):
    karneler = list(SinavSonucu.objects.filter(ogrenci__ogrenci_id=ogrenci_id).values('sinav__sinav_adi', 'toplam_puan', 'ai_karari'))
    return JsonResponse({'ogrenci_id': ogrenci_id, 'sonuclar': karneler})

# API 7: Spesifik Sınavın Puan Listesi (Dinamik Parametreli)
def api_sinav_detay(request, sinav_id):
    sonuclar = list(SinavSonucu.objects.filter(sinav__sinav_id=sinav_id).values('ogrenci__ogrenci_id', 'toplam_puan', 'ai_karari'))
    return JsonResponse({'sinav_id': sinav_id, 'sonuclar': sonuclar})

# API 8: Bir Akademisyenin Verdiği Dersler
def api_akademisyen_dersler(request, akad_id):
    hoca = Akademisyen.objects.filter(akademisyen_id=akad_id).first()
    if hoca:
        dersler = list(hoca.verdigi_dersler.values('ders_id', 'ders_adi'))
        return JsonResponse({'akademisyen_id': akad_id, 'dersler': dersler})
    return JsonResponse({'hata': 'Akademisyen bulunamadı'}, status=404)

# API 9: Sistemin Genel İstatistikleri (Hocaya Şov)
def api_genel_istatistik(request):
    toplam_kagit = SinavSonucu.objects.count()
    ortalama = SinavSonucu.objects.aggregate(Avg('toplam_puan'))['toplam_puan__avg'] or 0
    return JsonResponse({
        'sistem_durumu': 'Aktif',
        'toplam_okunan_kagit': toplam_kagit,
        'genel_basari_ortalamasi': round(ortalama, 2)
    })