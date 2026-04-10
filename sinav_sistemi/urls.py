from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # okuyucu/ ile başlayan her şeyi okuyucu uygulamasının kendi urls dosyasına yolla
    path('okuyucu/', include('okuyucu.urls')), 
]