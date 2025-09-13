# app_name/services/ocr_service.py
import easyocr

reader = easyocr.Reader(['es', 'en'])  # puedes ajustar idiomas

def extract_text_from_image(image_path: str) -> str:
    results = reader.readtext(image_path)
    text = " ".join([res[1] for res in results])  # concatenar resultados
    return text
