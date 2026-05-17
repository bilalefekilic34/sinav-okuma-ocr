from paddleocr import PaddleOCR
ocr_model = PaddleOCR(use_textline_orientation=True, lang='en')
result = list(ocr_model.predict("test.jpeg"))
for res in result:
    print(res)
