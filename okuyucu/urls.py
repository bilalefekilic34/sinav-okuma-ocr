from django.urls import path
from . import views # Nokta (.), "benimle aynı klasördeki views dosyasını getir" demektir.

app_name = 'okuyucu'

urlpatterns = [
    path('', views.ana_sayfa, name='ana_sayfa'),
    path('api/yukle/', views.sinav_yukle_api, name='sinav_yukle_api'),
]   