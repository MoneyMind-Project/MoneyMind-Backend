import google.generativeai as genai
from moneymind_apps.movements.utils.config import GOOGLE_API_KEY
import json
from moneymind_apps.movements.models import Category

genai.configure(api_key=GOOGLE_API_KEY)


def analyze_expense(image_path: str):
    """
    Envía una imagen a Gemini y devuelve un JSON con info del recibo.
    Si no se puede leer correctamente, retorna un mensaje de error.
    """
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = """
    Analiza este recibo y devuelve SOLO un JSON con esta estructura:
    {
      "category": "CATEGORIA_ESPECIFICA",
      "place": "...",
      "date": "YYYY-MM-DD",
      "time": "HH:mm",
      "total": número,
      "comment": "Texto opcional con algún detalle adicional o null"
    }

    Las 16 categorías válidas son:

    GASTOS ESENCIALES:
    - VIVIENDA: alquiler, hipoteca, mantenimiento, reparaciones
    - SERVICIOS_BASICOS: agua, luz, gas, internet, teléfono
    - ALIMENTACION: compras de supermercado, abarrotes, comida en casa
    - TRANSPORTE: gasolina, pasajes, estacionamiento, mantenimiento del vehículo
    - SALUD: seguros médicos, medicinas, consultas, emergencias

    GASTOS PERSONALES:
    - ENTRETENIMIENTO: cine, conciertos, bares, actividades recreativas
    - STREAMING_SUSCRIPCIONES: Netflix, Spotify, Amazon Prime, etc.
    - MASCOTAS: alimento, veterinario, accesorios
    - CUIDADO_PERSONAL: peluquería, gimnasio, spa, ropa, cosméticos

    FINANCIEROS:
    - DEUDAS_PRESTAMOS: cuotas de crédito, intereses
    - AHORRO_INVERSION: cuentas de ahorro, fondos mutuos, criptomonedas, aportes para jubilación
    - SEGUROS: de vida, auto, vivienda, otros seguros

    EDUCACION:
    - EDUCACION_DESARROLLO: cursos, talleres, libros, capacitaciones, colegiaturas, materiales, universidad, colegio

    OTROS:
    - REGALOS_CELEBRACIONES: cumpleaños, fiestas, donaciones
    - VIAJES_VACACIONES: boletos, hospedaje, actividades turísticas
    - IMPREVISTOS: emergencias, reparaciones no planificadas

     Instrucciones CRÍTICAS:
    - La clave "category" debe estar en MINÚSCULAS con guiones bajos (ejemplo: deudas_prestamos, NO DEUDAS_PRESTAMOS).
    - Si no puedes leer un campo, déjalo en null.
    - No escribas nada más fuera del JSON.
    - Asegúrate de elegir la categoría más específica según el contenido del recibo.
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
                json_text = result[start:end + 1]
                data = json.loads(json_text)

                # Validar que la categoría exista
                try:
                    Category(data.get("category"))
                except ValueError:
                    return {
                        "error": f"Categoría inválida: {data.get('category')}. Debe ser una de las 16 categorías definidas.",
                        "raw": result
                    }

                return data

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
    model = genai.GenerativeModel("gemini-2.5-flash")

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
