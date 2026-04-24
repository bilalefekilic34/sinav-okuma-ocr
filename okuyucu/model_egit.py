import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib
import os

# 100'lük dosyayı okuyoruz
df = pd.read_csv("ground_truth_100.csv")
X = df[['soru_1', 'soru_2', 'soru_3', 'soru_4', 'soru_5']]
y = (df['toplam_puan'] >= 50).astype(int)

# %80 Eğitim, %20 Test ayrımı
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42)

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Modeli kaydet
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
joblib.dump(model, os.path.join(base_dir, "ogrenci_analiz_modeli.pkl"))

print(f"✅ Model 80 veriyle eğitildi. 20 veri 'hiç görülmemiş' olarak ayrıldı.")