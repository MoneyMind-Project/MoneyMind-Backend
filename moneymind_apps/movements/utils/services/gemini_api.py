import google.generativeai as genai
from moneymind_apps.movements.utils.config import GOOGLE_API_KEY
import json
from moneymind_apps.movements.models import *
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, Avg

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


def generate_weekly_tip(user_id: int) -> str:
    """
    Genera un tip personalizado basado en el comportamiento de los últimos 30 días
    """
    from datetime import datetime, timedelta

    # Fecha de hace 30 días
    thirty_days_ago = datetime.now() - timedelta(days=30)

    # 1. Total gastado en últimos 30 días
    total_spent = Expense.objects.filter(
        user_id=user_id,
        date__gte=thirty_days_ago.date()
    ).aggregate(total=Sum('total'))['total'] or Decimal('0')
    total_spent = float(total_spent)

    # 2. Categoría con mayor gasto
    top_category = Expense.objects.filter(
        user_id=user_id,
        date__gte=thirty_days_ago.date()
    ).values('category').annotate(
        total=Sum('total')
    ).order_by('-total').first()

    top_category_name = ""
    top_category_amount = 0
    if top_category:
        try:
            cat_enum = Category(top_category['category'])
            top_category_name = CATEGORY_LABELS.get(cat_enum, top_category['category'])
            top_category_amount = float(top_category['total'])
        except ValueError:
            pass

    # 3. Promedio de gasto diario
    days_with_expenses = Expense.objects.filter(
        user_id=user_id,
        date__gte=thirty_days_ago.date()
    ).values('date').distinct().count()

    avg_daily_spend = total_spent / 30 if days_with_expenses > 0 else 0

    # 4. Número de transacciones
    transaction_count = Expense.objects.filter(
        user_id=user_id,
        date__gte=thirty_days_ago.date()
    ).count()

    # 5. Categorías más frecuentes (top 3)
    frequent_categories = Expense.objects.filter(
        user_id=user_id,
        date__gte=thirty_days_ago.date()
    ).values('category').annotate(
        count=Count('id')
    ).order_by('-count')[:3]

    frequent_categories_list = []
    for cat in frequent_categories:
        try:
            cat_enum = Category(cat['category'])
            cat_name = CATEGORY_LABELS.get(cat_enum, cat['category'])
            frequent_categories_list.append(f"{cat_name} ({cat['count']} veces)")
        except ValueError:
            pass

    # Crear el prompt para Gemini
    model = genai.GenerativeModel("gemini-2.0-flash-exp")

    prompt = f"""
Eres un asesor financiero experto. Genera UN ÚNICO consejo financiero personalizado y práctico basado en estos datos de comportamiento de los últimos 30 días:

DATOS DEL USUARIO:
- Total gastado: S/ {total_spent:.2f}
- Categoría con mayor gasto: {top_category_name} (S/ {top_category_amount:.2f})
- Promedio de gasto diario: S/ {avg_daily_spend:.2f}
- Número de transacciones: {transaction_count}
- Categorías más frecuentes: {', '.join(frequent_categories_list) if frequent_categories_list else 'No hay datos'}

INSTRUCCIONES:
1. Genera un consejo específico y accionable de máximo 2-3 oraciones
2. El consejo debe estar relacionado directamente con los datos proporcionados
3. Usa un tono amigable y motivador
4. Enfócate en el área que más puede mejorar (mayor gasto o más frecuente)
5. Da recomendaciones concretas y realistas
6. NO uses emojis
7. NO uses encabezados ni formato especial
8. Devuelve SOLO el texto del consejo, sin preámbulos maximo 30 palabras

Ejemplos de buenos consejos:
- "Has gastado S/ 450 en Entretenimiento este mes. Considera reducir salidas a restaurantes a 2 veces por semana y cocinar más en casa para ahorrar hasta S/ 200."
- "Tus gastos en Transporte han aumentado un 30%. Evalúa usar transporte público o compartir viajes para reducir costos."
- "Has realizado 15 compras pequeñas en Alimentación. Planifica tus compras semanalmente para evitar gastos impulsivos."

Genera el consejo ahora:
"""

    try:
        response = model.generate_content(prompt)
        tip = response.text.strip() if response and response.text else "Revisa tus gastos semanalmente para mantener el control de tu presupuesto."

        # Limpiar cualquier formato markdown que pudiera venir
        tip = tip.replace('**', '').replace('*', '').replace('#', '').strip()

        return tip

    except Exception as e:
        print(f"Error generando tip con Gemini: {str(e)}")
        return "Revisa tus gastos semanalmente y ajusta tu presupuesto según tus necesidades."

def _generate_all_chart_comments(chart_data_list):
    """
    Genera 5 comentarios en una sola llamada a Gemini.
    Retorna una lista de 5 strings.
    """
    prompt = f"""
    Eres un asistente experto en análisis de datos financieros y reportes.
    A continuación tienes 5 conjuntos de datos representando distintos gráficos.

    Por favor genera una breve descripción (una solo parrafo) para cada gráfico.
    Devuelve los 5 resultados en formato texto, separados exactamente por el delimitador '||'.

    1️⃣ Gráfico de predicción de gastos por mes: {chart_data_list[0]}
    2️⃣ Gráfico de distribución de gastos por minicategorías: {chart_data_list[1]}
    3️⃣ Gráfico de proporción de categorías padres: {chart_data_list[2]}
    4️⃣ Gráfico de evolución de ahorro: {chart_data_list[3]}
    5️⃣ Gráfico de gastos esenciales vs no esenciales: {chart_data_list[4]}

    Ejemplo de salida esperada:
    "Las ventas aumentaron un 20% este mes.||Los gastos se mantuvieron estables.||..."
    (Se detallista con los datos, usa aproximadamente 30 a 40 palabras para la descripcion)
    """

    model = genai.GenerativeModel("gemini-2.0-flash-exp")

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        comments = [c.strip() for c in text.split("||")]

        # Asegura que devuelva exactamente 5 elementos
        while len(comments) < 5:
            comments.append("Comentario no disponible")

        return comments[:5]

    except Exception as e:
        print("Error en _generate_all_chart_comments:", e)
        return ["Error al generar comentario"] * 5


