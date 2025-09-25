import google.generativeai as genai
from moneymind_apps.movements.utils.config import GOOGLE_API_KEY
import json

genai.configure(api_key=GOOGLE_API_KEY)

def analyze_expense(image_path: str):
    """
    Envía una imagen a Gemini y devuelve un JSON con info del recibo.
    Si no se puede leer correctamente, retorna un mensaje de error.
    """
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = """
    Analiza este recibo y devuelve SOLO un JSON con esta estructura:
    {
      "category": "GASTOS_ESENCIALES | GASTOS_PERSONALES | FINANCIEROS | EDUCACION | OTROS",
      "place": "...",
      "date": "YYYY-MM-DD",
      "time": "HH:mm",
      "total": número,
      "comment": "Texto opcional con algún detalle adicional o Null"
    }

    Guía para clasificar en "category":
    1. GASTOS_ESENCIALES → vivienda, servicios básicos, alimentación, transporte, salud.
    2. GASTOS_PERSONALES → entretenimiento, streaming, mascotas, cuidado personal.
    3. FINANCIEROS → deudas y préstamos, ahorro e inversión, seguros.
    4. EDUCACION → cursos, talleres, libros, colegiaturas.
    5. OTROS → regalos y celebraciones, viajes y vacaciones, imprevistos.

    Instrucciones:
    - La clave "category" debe corresponder exactamente a una de las 5 categorías principales.
    - Si no puedes leer un campo, déjalo en Null.
    - No escribas nada más fuera del JSON.
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


def analyze_income(image_path: str):
    """
    Envía una imagen a Gemini y devuelve un JSON con info del ingreso.
    Si no se puede leer correctamente, retorna un mensaje de error.
    """
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = """
    Analiza este comprobante/recibo de INGRESO y devuelve SOLO un JSON con esta estructura:
    {
      "title": "Fuente principal del ingreso (ej: 'Sueldo', 'Venta de producto', 'Intereses bancarios', 'Devolución', etc.)",
      "date": "YYYY-MM-DD",
      "time": "HH:mm",
      "total": número,
      "comment": "Texto opcional con algún detalle adicional o Null"
    }

    Guía para 'title':
    - Usa 'Sueldo' o 'Salario' si parece un pago laboral.
    - Usa 'Venta' si corresponde a venta de producto o servicio.
    - Usa 'Intereses' si es un ingreso bancario/financiero.
    - Usa 'Devolución' si es un reembolso o devolución de dinero.
    - Si no puedes identificarlo, escribe un título genérico como 'Ingreso'.

    Instrucciones:
    - Si no puedes leer un campo, déjalo en Null.
    - Devuelve únicamente el JSON, sin texto adicional.
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
            return {"error": "El comprobante no pudo ser analizado. Respuesta vacía."}

        # Intentar parsear a JSON (limpiando basura alrededor)
        try:
            start = result.find("{")
            end = result.rfind("}")
            if start != -1 and end != -1:
                json_text = result[start:end+1]
                return json.loads(json_text)

            return {"error": "El modelo no devolvió un JSON válido.", "raw": result}

        except json.JSONDecodeError:
            return {"error": "El modelo devolvió un JSON malformado.", "raw": result}

    except Exception as e:
        return {"error": f"Ocurrió un problema al analizar el ingreso: {str(e)}"}
