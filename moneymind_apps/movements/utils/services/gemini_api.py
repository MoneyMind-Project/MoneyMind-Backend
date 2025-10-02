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
      "valid": true/false,
      "validation_error": "mensaje si valid=false, null si valid=true",
      "category": "CATEGORIA_ESPECIFICA",
      "place": "...",
      "date": "YYYY-MM-DD",
      "time": "HH:mm",
      "total": número,
      "comment": "Texto opcional con algún detalle adicional o null"
    }

    VALIDACIONES CRÍTICAS (SOLO marca valid=false si se cumple alguna de estas):
    1. La imagen está COMPLETAMENTE BORROSA o ILEGIBLE y no se puede distinguir NADA. Solo marca valid=false con validation_error: "La imagen está demasiado borrosa. Por favor, toma una foto más clara." si literalmente no puedes leer NINGÚN texto.
    2. La imagen claramente NO ES UN DOCUMENTO DE GASTO (es una selfie, paisaje, meme, captura de chat, etc.). Marca valid=false con validation_error: "La imagen no corresponde a un recibo o comprobante de pago." SOLO si es obvio que no es un documento financiero.
    3. NO hay ningún número que pueda ser un monto. Marca valid=false con validation_error: "No se puede identificar ningún monto en la imagen." SOLO si no existe ningún número visible que pueda interpretarse como precio o total.

    IMPORTANTE: Si la imagen ES un recibo/boleta/factura pero falta información (lugar, fecha, hora, categoria,  etc.), NO marques valid=false. Simplemente deja esos campos en null. La falta de información NO es motivo para rechazar la imagen si claramente es un documento de gasto.

    Las 16 categorías válidas son (usa MINÚSCULAS con guiones bajos):

    GASTOS ESENCIALES:
    - vivienda: alquiler, hipoteca, mantenimiento, reparaciones
    - servicios_basicos: agua, luz, gas, internet, teléfono
    - alimentacion: compras de supermercado, abarrotes, comida en casa
    - transporte: gasolina, pasajes, estacionamiento, mantenimiento del vehículo
    - salud: seguros médicos, medicinas, consultas, emergencias

    GASTOS PERSONALES:
    - entretenimiento: cine, conciertos, bares, actividades recreativas
    - streaming_suscripciones: Netflix, Spotify, Amazon Prime, etc.
    - mascotas: alimento, veterinario, accesorios
    - cuidado_personal: peluquería, gimnasio, spa, ropa, cosméticos

    FINANCIEROS:
    - deudas_prestamos: cuotas de crédito, intereses
    - ahorro_inversion: cuentas de ahorro, fondos mutuos, criptomonedas, aportes para jubilación
    - seguros: de vida, auto, vivienda, otros seguros

    EDUCACION:
    - educacion_desarrollo: cursos, talleres, libros, capacitaciones, colegiaturas, materiales, universidad, colegio

    OTROS:
    - regalos_celebraciones: cumpleaños, fiestas, donaciones
    - viajes_vacaciones: boletos, hospedaje, actividades turísticas
    - imprevistos: emergencias, reparaciones no planificadas

    Instrucciones:
    - Si la imagen ES un documento de gasto pero falta información, marca valid=true y pon null en los campos que no puedas leer
    - La categoría debe estar en minúsculas con guiones bajos
    - Haz tu mejor esfuerzo por inferir la categoría incluso con información parcial, si no encuentras una categoria valida pon valid=true y pon null en el campo
    - No escribas nada más fuera del JSON
    """

    try:
        with open(image_path, "rb") as img_file:
            image_bytes = img_file.read()

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
            return {"error": "El recibo no pudo ser analizado. Respuesta vacía.", "code": "EMPTY_RESPONSE"}

        try:
            start = result.find("{")
            end = result.rfind("}")
            if start != -1 and end != -1:
                json_text = result[start:end + 1]
                data = json.loads(json_text)

                # Si la imagen no es válida según Gemini
                if not data.get("valid", True):
                    return {
                        "error": data.get("validation_error", "La imagen no pudo ser validada."),
                        "code": "INVALID_IMAGE"
                    }

                # Normalizar la categoría a minúsculas si existe
                if "category" in data and data["category"]:
                    data["category"] = data["category"].lower()
                else:
                    data["category"] = None  # 👈 si no existe, se queda en null

                # 👇 Eliminamos la validación estricta de categoría
                return data

            return {"error": "El modelo no devolvió un JSON válido.", "code": "INVALID_JSON"}

        except json.JSONDecodeError:
            return {"error": "El modelo devolvió un JSON malformado.", "code": "MALFORMED_JSON"}

    except Exception as e:
        return {"error": f"Ocurrió un problema al analizar el recibo: {str(e)}", "code": "UNEXPECTED_ERROR"}


def analyze_income(image_path: str):
    """
    Envía una imagen a Gemini y devuelve un JSON con info del ingreso.
    """
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = """
    Analiza este comprobante/recibo de INGRESO y devuelve SOLO un JSON con esta estructura:
    {
      "valid": true/false,
      "validation_error": "mensaje si valid=false, null si valid=true",
      "title": "Fuente principal del ingreso",
      "date": "YYYY-MM-DD",
      "time": "HH:mm",
      "total": número,
      "comment": "Texto opcional con algún detalle adicional o null"
    }

    VALIDACIONES CRÍTICAS (SOLO marca valid=false si se cumple alguna de estas):
    1. La imagen está COMPLETAMENTE BORROSA o ILEGIBLE y no se puede distinguir NADA. Solo marca valid=false con validation_error: "La imagen está demasiado borrosa. Por favor, toma una foto más clara." si literalmente no puedes leer NINGÚN texto.
    2. La imagen claramente NO ES UN DOCUMENTO DE INGRESO (es una selfie, paisaje, meme, captura de chat, etc.). Marca valid=false con validation_error: "La imagen no corresponde a un comprobante de ingreso." SOLO si es obvio que no es un documento financiero.
    3. NO hay ningún número que pueda ser un monto. Marca valid=false con validation_error: "No se puede identificar ningún monto en la imagen." SOLO si no existe ningún número visible que pueda interpretarse como cantidad recibida.

    IMPORTANTE: Si la imagen ES un comprobante de ingreso pero falta información (fecha, hora, detalles, etc.), NO marques valid=false. Simplemente deja esos campos en null. La falta de información NO es motivo para rechazar la imagen si claramente es un documento de ingreso.

    Guía para 'title':
    - 'Sueldo' o 'Salario' si parece un pago laboral
    - 'Venta' si corresponde a venta de producto o servicio
    - 'Intereses' si es un ingreso bancario/financiero
    - 'Devolución' si es un reembolso
    - 'Transferencia' si es una transferencia bancaria
    - 'Ingreso' como título genérico si no se puede identificar

    Instrucciones:
    - Si la imagen ES un documento de ingreso pero falta información, marca valid=true y pon null en los campos que no puedas leer
    - Haz tu mejor esfuerzo por poner un título descriptivo incluso con información parcial
    - Si no puedes leer un campo, déjalo en null
    - Devuelve únicamente el JSON, sin texto adicional
    """

    try:
        with open(image_path, "rb") as img_file:
            image_bytes = img_file.read()

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
            return {"error": "El comprobante no pudo ser analizado. Respuesta vacía.", "code": "EMPTY_RESPONSE"}

        try:
            start = result.find("{")
            end = result.rfind("}")
            if start != -1 and end != -1:
                json_text = result[start:end+1]
                data = json.loads(json_text)

                # Si la imagen no es válida según Gemini
                if not data.get("valid", True):
                    return {
                        "error": data.get("validation_error", "La imagen no pudo ser validada."),
                        "code": "INVALID_IMAGE"
                    }

                return data

            return {"error": "El modelo no devolvió un JSON válido.", "code": "INVALID_JSON"}

        except json.JSONDecodeError:
            return {"error": "El modelo devolvió un JSON malformado.", "code": "MALFORMED_JSON"}

    except Exception as e:
        return {"error": f"Ocurrió un problema al analizar el ingreso: {str(e)}", "code": "UNEXPECTED_ERROR"}
