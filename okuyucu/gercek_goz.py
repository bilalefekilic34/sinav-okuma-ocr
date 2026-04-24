import os
import torch
import warnings
from transformers import AutoModel, AutoTokenizer, BitsAndBytesConfig

# Dırdırları sustur
warnings.filterwarnings("ignore")
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

print("🔍 [SİSTEM] DeepSeek Saf Göz Testi V2 Başlıyor...")

# 1. KESİN DOSYA YOLU KONTROLÜ
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
resim_yolu = os.path.join(BASE_DIR, "test_veriseti_60", "tablo_4248.jpg")

if not os.path.exists(resim_yolu):
    print(f"\n❌ KRİTİK HATA: Resim bulunamadı!")
    print(f"Aradığım tam yol: {resim_yolu}")
    print("Lütfen 'test_veriseti_60' klasörünün şu anki dizinde olduğundan emin ol.")
    exit()

print(f"\n✅ Resim başarıyla bulundu! (Boyut: {os.path.getsize(resim_yolu)} byte)")
print("⚙️ Model Yükleniyor...")

model_name = 'deepseek-ai/DeepSeek-OCR-2'
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True, local_files_only=True)

q_config = BitsAndBytesConfig(
    load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True, bnb_4bit_quant_type="nf4"
)

model = AutoModel.from_pretrained(
    model_name, trust_remote_code=True, use_safetensors=True,
    quantization_config=q_config, device_map="cuda",
    torch_dtype=torch.bfloat16, local_files_only=True
).eval()

print("⏳ Model kağıdı okuyor...")
prompt = "<image>\n<|grounding|>Convert the document to markdown."

with torch.no_grad():
    with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
        # 2. SAVE_RESULTS = TRUE YAPILDI
        res = model.infer(
            tokenizer, prompt=prompt, image_file=resim_yolu,
            output_path=BASE_DIR, base_size=1024, image_size=768,
            crop_mode=True, save_results=True 
        )

print("\n" + "="*60)
print("👀 ÇIKTI (RETURN DEĞERİ):")
print(res)
print("="*60)