import google.generativeai as genai
from moneymind_apps.receipts.utils.config import GOOGLE_API_KEY

genai.configure(api_key=GOOGLE_API_KEY)

def analizar_recibo(image_path: str):
    """
    Envía una imagen a Gemini y devuelve un JSON con info del recibo
    """
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = """
    Analiza este recibo y devuelve SOLO un JSON con esta estructura:
    {
      "Lugar": "...",
      "Hora": "...",
      "Total": "..."
    }
    No escribas nada más fuera del JSON.
    """

    # 🔑 leer la imagen como bytes
    with open(image_path, "rb") as img_file:
        image_bytes = img_file.read()

    # Enviar a Gemini (prompt + imagen en bytes)
    response = model.generate_content(
        [
            {"role": "user", "parts": [prompt, {"mime_type": "image/jpeg", "data": image_bytes}]}
        ]
    )

    return response.text.strip()
