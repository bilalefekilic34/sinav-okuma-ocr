import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
from ai_engine import SinavMotoru 

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_YOLU = os.path.join(BASE_DIR, "ground_truth_100.csv")
TEST_KLASORU = os.path.join(BASE_DIR, "test_veriseti_100")

def tam_test_baslat():
    print("🔍 [SİSTEM] 100 Kağıtlık Dev Analiz Başlıyor...")
    df_gt = pd.read_csv(CSV_YOLU)
    motor = SinavMotoru()
    
    TP, TN, FP, FN = 0, 0, 0, 0
    toplam = len(df_gt)

    for index, row in df_gt.iterrows():
        resim_yolu = os.path.join(TEST_KLASORU, row['dosya_adi'])
        if not os.path.exists(resim_yolu): continue

        tahmin = motor.kagidi_oku_ve_degerlendir(resim_yolu)
        ai_karar = 1 if tahmin.get('yapay_zeka_karari') == "Geçti" else 0
        gercek_karar = 1 if int(row['toplam_puan']) >= 50 else 0

        if gercek_karar == 1 and ai_karar == 1: TP += 1
        elif gercek_karar == 0 and ai_karar == 0: TN += 1
        elif gercek_karar == 0 and ai_karar == 1: FP += 1
        elif gercek_karar == 1 and ai_karar == 0: FN += 1
        
        print(f"[{index+1}/100] İşleniyor: {row['dosya_adi']}")
    
    accuracy = (TP + TN) / toplam
    precision = TP / (TP + FP)
    recall = TP / (TP + FN)
    f1 = (2 * (precision * recall)) / (precision + recall)

    # --- RAPORLAMA ---
    print(f"TP: {TP}")
    print(f"TN: {TN}")
    print(f"FP: {FP}")
    print(f"FN: {FN}")
    print("\n" + "="*55)
    print(" 📊 NİHAİ PERFORMANS RAPORU (SADECE EL YAZISI TABLOLAR)")
    print("="*55)
    print(f"✅ Doğru Tespitler (TP+TN) : {TP+TN}")
    print(f"❌ Hatalı Kararlar (FP+FN) : {FP+FN}")
    print("-" * 55)
    print(f"🎯 Accuracy (Doğruluk)     : %{accuracy*100:.2f}")
    print(f"🎯 Precision (Kesinlik)    : %{precision*100:.2f}")
    print(f"🎯 Recall (Duyarlılık)     : %{recall*100:.2f}")
    print(f"🎯 F1-Score               : {f1:.3f}")
    print("="*55)

    # --- GÖRSEL MATRİS KAYDI ---
    plt.figure(figsize=(8, 6))
    sns.heatmap([[TN, FP], [FN, TP]], annot=True, fmt='d', cmap='Greens',
                xticklabels=['Tahmin: KALDI', 'Tahmin: GEÇTİ'], 
                yticklabels=['Gerçek: KALDI', 'Gerçek: GEÇTİ'])
    plt.title(f'DeepSeek-OCR-2 Karar Matrisi\nAccuracy: %{accuracy*100:.1f}')
    
    matrix_yolu = os.path.join(BASE_DIR, "confusion_matrix_final.png")
    plt.savefig(matrix_yolu, dpi=300)
    print(f"\n🖼️ Matris görseli kaydedildi: {matrix_yolu}")

if __name__ == "__main__":
    tam_test_baslat()