from django.urls import path
from . import views # Nokta (.), "benimle aynı klasördeki views dosyasını getir" demektir.

app_name = 'okuyucu'

urlpatterns = [
    path('', views.ana_sayfa, name='ana_sayfa'),
    path('api/yukle/', views.sinav_yukle_api, name='sinav_yukle_api'),
    path('api/ogrenciler/', views.api_ogrenciler, name='api_ogrenciler'),
    path('api/dersler/', views.api_dersler, name='api_dersler'),
    path('api/sinavlar/', views.api_sinavlar, name='api_sinavlar'),
    path('api/akademisyenler/', views.api_akademisyenler, name='api_akademisyenler'),
    path('api/sonuclar/', views.api_sonuclar, name='api_sonuclar'),
    path('api/ogrenci/<str:ogrenci_id>/', views.api_ogrenci_detay, name='api_ogrenci_detay'),
    path('api/sinav/<str:sinav_id>/', views.api_sinav_detay, name='api_sinav_detay'),
    path('api/hoca/<str:akad_id>/dersler/', views.api_akademisyen_dersler, name='api_akademisyen_dersler'),
    path('api/istatistik/', views.api_genel_istatistik, name='api_genel_istatistik'),
]   