from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.db.models import Avg, Count, Q  # İstatistikler için eklendi!
import os
from .models import SinavSonucu, Ogrenci, Sinav, Ders, Akademisyen
import random

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
        # Yetki Filtresi: Admin değilse yetkisi olanları getir
        if not request.user.is_superuser and hasattr(request.user, 'akademisyen_profili'):
            sonuclar = SinavSonucu.objects.filter(sinav_id=sinav_id, sinav__ders__akademisyenler__user=request.user).select_related('ogrenci', 'sinav__ders')
        else:
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
        if not request.user.is_superuser and hasattr(request.user, 'akademisyen_profili'):
            sonuclar = SinavSonucu.objects.filter(ogrenci_id=ogrenci_no, sinav__ders__akademisyenler__user=request.user).select_related('sinav', 'sinav__ders')
        else:
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
def kagit_yukle(request):
    if request.method == 'GET':
        return render(request, 'kagit_yukle.html')

    from .ai_engine import SinavMotoru 
    motor = SinavMotoru()

    if request.method == 'POST' and request.FILES.get('sinav_kagidi'):
        yuklenen_kagit = request.FILES['sinav_kagidi']
        
        # Resmi static klasörüne kaydet ki önizlemede görünsün
        import os
        hedef_klasor = os.path.join(os.path.dirname(__file__), 'static', 'temp_uploads')
        os.makedirs(hedef_klasor, exist_ok=True)
        gecici_yol = os.path.join(hedef_klasor, yuklenen_kagit.name)
        
        with open(gecici_yol, 'wb+') as hedef:
            for chunk in yuklenen_kagit.chunks():
                hedef.write(chunk)
                
        sonuclar = motor.kagidi_oku_ve_degerlendir(gecici_yol)
        
        if sonuclar.get("durum") == "basarili":
            # Veritabanına YAZMIYORUZ. Session'a kaydedip önizlemeye geçiyoruz.
            request.session['temp_sonuclar'] = sonuclar
            request.session['temp_resim'] = f"/static/temp_uploads/{yuklenen_kagit.name}"
            return JsonResponse({"durum": "basarili", "yonlendir": "/okuyucu/onizleme/"})
        else:
            return JsonResponse({"durum": "hata", "mesaj": "Sınav ID veya Öğrenci No okunamadı."})
            
    return JsonResponse({"durum": "hata", "mesaj": "Sadece POST isteği ve 'sinav_kagidi' dosyası kabul edilir."})

# Geriye dönük uyumluluk veya saf API kullanımı (opsiyonel)
@csrf_exempt 
def sinav_yukle_api(request):
    return JsonResponse({"durum": "hata", "mesaj": "Bu uç nokta kapatıldı. Yeni kagit-yukle rotasını kullanınız."})

@csrf_exempt
def onizleme_sayfasi(request):
    # Eğer sonuç yoksa ana sayfaya dön
    if 'temp_sonuclar' not in request.session:
        return render(request, 'index.html', {'mesaj': 'Önizleme bulunamadı.', 'baslik': ''})
        
    sonuclar = request.session['temp_sonuclar']
    resim_url = request.session.get('temp_resim', '')
    
    if request.method == 'POST':
        # Kullanıcı formdan düzenleyip onayladıysa DB'ye yaz
        s_id = request.POST.get("sinav_id")
        o_no = request.POST.get("ogrenci_no")
        ai_karari = request.POST.get("yapay_zeka_karari", "Bilinmiyor")
        
        # Dinamik soruları topla
        sorular_dict = {}
        toplam_puan = 0
        for key, value in request.POST.items():
            if key.startswith("soru_"):
                q_num = key.replace("soru_", "")
                try:
                    puan = int(value)
                    sorular_dict[q_num] = puan
                    toplam_puan += puan
                except:
                    pass
        
        # Öğrenci ve Sınav oluştur (Yoksa)
        ders, _ = Ders.objects.get_or_create(ders_id="BLG101", defaults={"ders_adi": "Otomatik Eklenen Ders"})
        sinav, _ = Sinav.objects.get_or_create(sinav_id=s_id, defaults={"ders": ders, "sinav_adi": "Tarandı"})
        ogrenci, _ = Ogrenci.objects.get_or_create(ogrenci_id=o_no, defaults={"ad_soyad": f"Öğrenci {o_no}"})
        
        SinavSonucu.objects.update_or_create(
            ogrenci=ogrenci,
            sinav=sinav,
            defaults={
                "sorular_ve_puanlar": sorular_dict,
                "toplam_puan": toplam_puan,
                "ai_karari": ai_karari,
                "onaylandi_mi": True
            }
        )
        
        # Session'ı temizle
        del request.session['temp_sonuclar']
        if 'temp_resim' in request.session:
            del request.session['temp_resim']
            
        return redirect(f"/okuyucu/?sinav_id={s_id}")

    # GET isteğinde önizleme sayfasını render et
    context = {
        'sonuclar': sonuclar,
        'resim_url': resim_url
    }
    return render(request, 'onizleme.html', context)

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

# --- RBAC VE CRUD İŞLEMLERİ ---
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

class OzelLoginView(LoginView):
    template_name = 'login.html'
    
    def get_success_url(self):
        return reverse_lazy('okuyucu:ana_sayfa')

class AkademisyenYetkiMixin(UserPassesTestMixin):
    def test_func(self):
        # Sadece hocalar ve adminler yetkili
        return self.request.user.is_authenticated and (self.request.user.is_superuser or hasattr(self.request.user, 'akademisyen_profili'))

# --- DERS CRUD ---
class DersListView(LoginRequiredMixin, AkademisyenYetkiMixin, ListView):
    model = Ders
    template_name = 'crud/ders_list.html'
    context_object_name = 'dersler'

class DersCreateView(LoginRequiredMixin, AkademisyenYetkiMixin, CreateView):
    model = Ders
    fields = ['ders_id', 'ders_adi']
    template_name = 'crud/form.html'
    success_url = reverse_lazy('okuyucu:ders_listesi')

# --- ÖĞRENCİ CRUD ---
class OgrenciListView(LoginRequiredMixin, AkademisyenYetkiMixin, ListView):
    model = Ogrenci
    template_name = 'crud/ogrenci_list.html'
    context_object_name = 'ogrenciler'

class OgrenciCreateView(LoginRequiredMixin, AkademisyenYetkiMixin, CreateView):
    model = Ogrenci
    fields = ['ogrenci_id', 'ad_soyad']
    template_name = 'crud/form.html'
    success_url = reverse_lazy('okuyucu:ogrenci_listesi')

# --- SINAV CRUD ---
class SinavListView(LoginRequiredMixin, AkademisyenYetkiMixin, ListView):
    model = Sinav
    template_name = 'crud/sinav_list.html'
    context_object_name = 'sinavlar'

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.filter(ders__akademisyenler__user=self.request.user)
        return qs

class SinavCreateView(LoginRequiredMixin, AkademisyenYetkiMixin, CreateView):
    model = Sinav
    fields = ['sinav_id', 'ders', 'sinav_adi']
    template_name = 'crud/form.html'
    success_url = reverse_lazy('okuyucu:sinav_listesi')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Hoca sadece kendi derslerine sınav ekleyebilir!
        if not self.request.user.is_superuser:
            form.fields['ders'].queryset = Ders.objects.filter(akademisyenler__user=self.request.user)
        return form

# --- GÖREV 5: ÖZEL FRONTEND ADMIN PANELİ ---
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages

def is_super_admin(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_super_admin, login_url='/okuyucu/login/')
def admin_dashboard(request):
    # Eğer User modeli yukarıda import edilmediyse hata vermesin diye buraya ekliyoruz
    from django.contrib.auth.models import User 

    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Olay 1: Yeni Akademisyen Ekle
        if action == 'add_akad':
            ad_soyad = request.POST.get('ad_soyad', '').strip()
            username = request.POST.get('username', '').strip()
            
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Hata: Bu kullanıcı adı zaten sistemde var.')
            else:
                isim_parcalari = ad_soyad.split()
                first = isim_parcalari[0] if isim_parcalari else "Eğitmen"
                last = " ".join(isim_parcalari[1:]) if len(isim_parcalari) > 1 else ""
                
                # Yeni User yarat
                user = User.objects.create_user(
                    username=username,
                    password="123456",
                    first_name=first,
                    last_name=last
                )
                # Akad profiline bağla
                Akademisyen.objects.create(
                    user=user,
                    akademisyen_id=username
                )
                messages.success(request, f'Tebrikler, {first} hocamız başarıyla eklendi! Şifresi: 123456')
                
        # Olay 2: Mevcut Hocaya Ders Ata
        elif action == 'assign_ders':
            akad_id = request.POST.get('akad_id')
            ders_ids = request.POST.getlist('ders_ids') # birden çok seçildiği için list
            
            try:
                akad = Akademisyen.objects.get(id=akad_id)
                secilen_dersler = Ders.objects.filter(pk__in=ders_ids)
                akad.verdigi_dersler.add(*secilen_dersler)
                messages.success(request, f'{akad.user.username} adlı akademisyene seçili dersler atandı.')
            except Exception as e:
                messages.error(request, 'Atama sırasında bir sorun oluştu.')
                
        # Olay 3: Hocadan Ders Çıkar (Yeni ve Akıllı Devir Teslim Mantığı)
        elif action == 'remove_ders':
            akad_id = request.POST.get('akad_id')
            ders_id = request.POST.get('ders_id')
            
            hoca = Akademisyen.objects.get(pk=akad_id)
            ders = Ders.objects.get(pk=ders_id)
            
            hoca.verdigi_dersler.remove(ders)
            yetim_kagitlar = SinavSonucu.objects.filter(akademisyen=hoca, sinav__ders=ders)
            etkilenen_sayi = yetim_kagitlar.count()
            
            if etkilenen_sayi > 0:
                diger_hocalar = list(Akademisyen.objects.filter(verdigi_dersler=ders).exclude(pk=hoca.pk))
                if diger_hocalar:
                    for kagit in yetim_kagitlar:
                        kagit.akademisyen = random.choice(diger_hocalar)
                        kagit.save()
                    messages.success(request, f"✅ {ders.ders_adi} dersi {hoca.user.username} adlı hocadan alındı. Elindeki {etkilenen_sayi} adet sınav kağıdı diğer hocalara otomatik devredildi.")
                else:
                    yetim_kagitlar.update(akademisyen=None)
                    messages.warning(request, f"⚠️ {ders.ders_adi} dersi alındı. Ancak bu dersi veren başka hoca olmadığı için {etkilenen_sayi} kağıt 'Atanmadı' durumuna düştü!")
            else:
                messages.success(request, f"✅ {ders.ders_adi} dersi başarıyla alındı.")

        # Olay 4: Hızlı Öğrenci Ekleme
        elif action == 'add_ogrenci':
            ogr_id = request.POST.get('ogrenci_id', '').strip()
            ad_soyad = request.POST.get('ad_soyad', '').strip()
            
            if Ogrenci.objects.filter(ogrenci_id=ogr_id).exists():
                messages.error(request, f'Hata: {ogr_id} numaralı öğrenci zaten sistemde kayıtlı!')
            else:
                Ogrenci.objects.create(ogrenci_id=ogr_id, ad_soyad=ad_soyad)
                messages.success(request, f'✅ {ad_soyad} ({ogr_id}) sisteme başarıyla eklendi. Şimdi aratarak ders atayabilirsiniz.')

        # Olay 5: Öğrenci Arama
        elif action == 'search_ogrenci':
            search_id = request.POST.get('search_id')
            found_ogrenci = Ogrenci.objects.filter(ogrenci_id=search_id).prefetch_related('kayitli_dersler').first()
            
            if not found_ogrenci:
                messages.error(request, f"ID: {search_id} olan bir öğrenci bulunamadı.")
            else:
                request.session['searched_ogrenci_id'] = search_id

        # Olay 6: Öğrenci Ders Güncelleme
        elif action == 'update_ogrenci_dersler':
            og_pk = request.POST.get('ogrenci_pk')
            yeni_ders_ids = request.POST.getlist('yeni_ders_ids')
            
            ogrenci = Ogrenci.objects.get(pk=og_pk)
            if len(yeni_ders_ids) != 3:
                messages.error(request, "Hata: Bir öğrencinin tam 3 dersi olmalıdır.")
            else:
                ogrenci.kayitli_dersler.set(Ders.objects.filter(pk__in=yeni_ders_ids))
                messages.success(request, f"{ogrenci.ogrenci_id} numaralı öğrencinin dersleri başarıyla güncellendi.")
            # Güncellemeden sonra öğrenci sekmesi kapanmasın diye ID'yi tekrar session'a veriyoruz
            request.session['searched_ogrenci_id'] = ogrenci.ogrenci_id 

        # İşlem bitince sayfayı yenile ki form tekrar gönderilmesin
        return redirect('okuyucu:admin_dashboard')

    # GET isteği için context öncesi öğrenci sorgusu kontrolü
    searched_ogrenci = None
    ogrenci_karnesi = None
    if 'searched_ogrenci_id' in request.session:
        s_id = request.session['searched_ogrenci_id']
        searched_ogrenci = Ogrenci.objects.filter(ogrenci_id=s_id).prefetch_related('kayitli_dersler').first()
        if searched_ogrenci:
            ogrenci_karnesi = SinavSonucu.objects.filter(ogrenci=searched_ogrenci).select_related('sinav', 'sinav__ders', 'akademisyen')
        del request.session['searched_ogrenci_id'] # Gösterdikten sonra hafızadan sil

    # GET isteği için genel context (İstatistikler ve Tablolar)
    context = {
        'toplam_ogrenci': Ogrenci.objects.count(),
        'toplam_akademisyen': Akademisyen.objects.count(),
        'toplam_ders': Ders.objects.count(),
        'toplam_sinav_kagidi': SinavSonucu.objects.filter(onaylandi_mi=True).count(),
        'akademisyenler': Akademisyen.objects.select_related('user').prefetch_related('verdigi_dersler').all(),
        'bostaki_akademisyenler': Akademisyen.objects.filter(verdigi_dersler__isnull=True).select_related('user').distinct(),
        'dersler': Ders.objects.all(),
        'searched_ogrenci': searched_ogrenci,
        'ogrenci_karnesi': ogrenci_karnesi,
    }
    return render(request, 'admin_dashboard.html', context)