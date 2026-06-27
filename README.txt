Django framework'u üstüne kurulu, yerel sisteminizde RapidOCR'ı çalıştıran bu proje sınav kağıtlarından sonuçların, öğrenci ID'si ve sınav ID'lerinin tek tek okunmasını tek aşamaya indirir.

Gerekli kütüphaneler için : 
- İşletim sisteminize göre Python sanal çevrenizi (venv) oluşturup aktif edin. 
- "pip install -r requirements.txt" ile kütüphanelerin kurulumunu tamamlayın.

Projeyi çalıştırmak için : 
- Projenin ana dizinindeyken "python manage.py runserver" komutunu çalıştırın. 

Kullanıcı (bu projede kullanıcı akademisyenler ve öğretim görevlileridir) sisteme sınav kağıtlarını yükler.
RapidOCR motoru kağıt başına yaklaşık 0.8 saniye ve %92 doğrulukla kağıtları okur.

Okuma işleminin ardından sistem kullanıcıya önizleme ekranı sunar, bu ekranda modelin yanlış okuduğu sonuçlar düzeltilir.
