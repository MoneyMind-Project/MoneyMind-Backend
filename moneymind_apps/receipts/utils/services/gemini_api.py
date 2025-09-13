import google.generativeai as genai
from moneymind_apps.receipts.utils.config import GOOGLE_API_KEY
import json

genai.configure(api_key=GOOGLE_API_KEY)

def analizar_recibo(image_path: str):
    """
    Envía una imagen a Gemini y devuelve un JSON con info del recibo.
    Si no se puede leer correctamente, retorna un mensaje de error.
    """
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = """
    Analiza este recibo y devuelve SOLO un JSON con esta estructura:
    {
      "Lugar": "...",
      "Hora": "...",
      "Total": "..."
    }
    Si no puedes leer un campo, escribe "No detectado".
    No escribas nada más fuera del JSON.
    """

    try:
        # Leer la imagen como bytes
        with open(image_path, "rb") as img_file:
            image_bytes = img_file.read()

        # Enviar a Gemini
        response = model.generate_content(
            [
                {
                    "role": "user",
                    "parts": [
                        prompt,
                        {"mime_type": "image/jpeg", "data": image_bytes},
                    ],
                }
            ]
        )

        result = response.text.strip() if response and response.text else None

        if not result:
            return {"error": "El recibo no pudo ser analizado. Respuesta vacía."}

        # Intentar parsear a JSON (limpiando basura alrededor)
        try:
            # Extraer el bloque JSON aunque haya texto alrededor
            start = result.find("{")
            end = result.rfind("}")
            if start != -1 and end != -1:
                json_text = result[start:end+1]
                return json.loads(json_text)

            return {"error": "El modelo no devolvió un JSON válido.", "raw": result}

        except json.JSONDecodeError:
            return {"error": "El modelo devolvió un JSON malformado.", "raw": result}

    except Exception as e:
        return {"error": f"Ocurrió un problema al analizar el recibo: {str(e)}"}
