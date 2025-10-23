from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from moneymind_apps.alerts.models import *
from django.shortcuts import get_object_or_404
from moneymind_apps.alerts.serializer import *
from django.utils.timezone import now
from datetime import date
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import calendar

class UserAlertsView(APIView):
    permission_classes = [AllowAny]
    """
    Obtiene las alertas/notificaciones del usuario
    """

    def get(self, request):
        user_id = request.query_params.get('user_id')
        seen = request.query_params.get('seen')  # Opcional: 'true', 'false'

        if not user_id:
            return Response(
                {"error": "user_id es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )

        alerts = Alert.objects.filter(user_id=user_id)

        # Filtrar por visto/no visto si se especifica
        if seen is not None:
            seen_bool = seen.lower() == 'true'
            alerts = alerts.filter(seen=seen_bool)

        alerts_data = [
            {
                "id": alert.id,
                "alert_type": alert.alert_type,
                "message": alert.message,
                "target_month": alert.target_month,
                "target_year": alert.target_year,
                "seen": alert.seen,
                "created_at": alert.created_at.isoformat()
            }
            for alert in alerts
        ]

        return Response(
            {
                "success": True,
                "data": alerts_data,
                "unread_count": alerts.filter(seen=False).count()
            },
            status=status.HTTP_200_OK
        )

    def patch(self, request):
        """
        Marca alertas como vistas
        """
        alert_ids = request.data.get('alert_ids', [])

        if not alert_ids:
            return Response(
                {"error": "alert_ids es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )

        Alert.objects.filter(id__in=alert_ids).update(seen=True)

        return Response(
            {"success": True, "message": "Alertas marcadas como vistas"},
            status=status.HTTP_200_OK
        )


class UserAlertsPaginationView(APIView):
    permission_classes = [AllowAny]
    """
    Obtiene las alertas/notificaciones del usuario con paginación
    """

    def get(self, request):
        user_id = request.query_params.get('user_id')
        seen = request.query_params.get('seen')  # Opcional: 'true', 'false'

        # Parámetros de paginación
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 5))

        if not user_id:
            return Response(
                {"error": "user_id es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if page < 1 or page_size < 1:
            return Response(
                {"error": "Los parámetros page y page_size deben ser >= 1"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Filtrar alertas del usuario (ya ordenadas por -created_at gracias al Meta del modelo)
        alerts = Alert.objects.filter(user_id=user_id)

        # Filtrar por visto/no visto si se especifica
        if seen is not None:
            seen_bool = seen.lower() == 'true'
            alerts = alerts.filter(seen=seen_bool)

        # Contar total antes de paginar
        total_count = alerts.count()
        unread_count = Alert.objects.filter(user_id=user_id, seen=False).count()

        # Calcular offset y aplicar paginación
        offset = (page - 1) * page_size
        alerts_page = alerts[offset:offset + page_size]

        # Serializar datos
        alerts_data = [
            {
                "id": alert.id,
                "alert_type": alert.alert_type,
                "message": alert.message,
                "target_month": alert.target_month,
                "target_year": alert.target_year,
                "seen": alert.seen,
                "created_at": alert.created_at.isoformat()
            }
            for alert in alerts_page
        ]

        # Calcular si hay más páginas
        has_more = (offset + page_size) < total_count

        return Response(
            {
                "success": True,
                "data": alerts_data,
                "unread_count": unread_count,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_alerts": total_count,
                    "loaded_count": len(alerts_data),
                    "has_more": has_more,
                    "next_page": page + 1 if has_more else None
                }
            },
            status=status.HTTP_200_OK
        )

    def patch(self, request):
        """
        Marca alertas como vistas
        """
        alert_ids = request.data.get('alert_ids', [])
        mark_all = request.data.get('mark_all', False)  # Nueva opción para marcar todas
        user_id = request.data.get('user_id')

        if mark_all and user_id:
            # Marcar todas las alertas del usuario como vistas
            Alert.objects.filter(user_id=user_id, seen=False).update(seen=True)
            return Response(
                {"success": True, "message": "Todas las alertas marcadas como vistas"},
                status=status.HTTP_200_OK
            )

        if not alert_ids:
            return Response(
                {"error": "alert_ids es requerido o use mark_all=true con user_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        Alert.objects.filter(id__in=alert_ids).update(seen=True)

        return Response(
            {"success": True, "message": "Alertas marcadas como vistas"},
            status=status.HTTP_200_OK
        )

class MarkAlertAsSeenView(APIView):
    permission_classes = [AllowAny]
    """
    Marca una alerta específica como vista (seen=True) para un usuario en específico.
    """

    def patch(self, request, user_id, alert_id):

        try:
            alert = get_object_or_404(Alert, id=alert_id, user_id=user_id)

            if not alert.seen:
                alert.seen = True
                alert.save(update_fields=['seen'])
                print("🟢 Alerta marcada como vista.")

            return Response(
                {
                    "success": True,
                    "message": f"Alerta {alert_id} marcada como vista para usuario {user_id}."
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {
                    "success": False,
                    "error": f"Error al marcar la alerta como vista: {str(e)}"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MarkAllRiskAlertsAsSeenView(APIView):
    permission_classes = [AllowAny]
    """
    Marca todas las alertas de tipo 'risk' de un usuario específico como vistas.
    El 'user_id' se recibe desde la URL.
    """

    def patch(self, request, user_id):
        """
        Actualiza todas las alertas de tipo 'risk' (seen=False → seen=True)
        pertenecientes al usuario indicado en la URL.
        """
        try:
            updated_count = Alert.objects.filter(
                user_id=user_id,
                alert_type='risk',
                seen=False
            ).update(seen=True)

            return Response(
                {
                    "success": True,
                    "updated_count": updated_count,
                    "message": f"{updated_count} alertas de tipo 'risk' marcadas como vistas para el usuario {user_id}."
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": f"Error al marcar alertas 'risk' como vistas: {str(e)}"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RecurringPaymentReminderCreateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RecurringPaymentSerializer(data=request.data)

        if serializer.is_valid():
            recurring_payment = serializer.save()

            return Response(
                {
                    "success": True,
                    "message": "Pago recurrente creado exitosamente",
                    "data": RecurringPaymentSerializer(recurring_payment).data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

class RecurringPaymentReminderListByUserView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            user_id = int(request.query_params.get("user_id"))
        except (TypeError, ValueError):
            return Response(
                {"success": False, "error": "El parámetro user_id es obligatorio y debe ser un número."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 🔹 Filtrar los recordatorios del usuario
        reminders = RecurringPaymentReminder.objects.filter(user_id=user_id)

        # 🔹 Serializar los resultados
        serializer = RecurringPaymentSerializer(reminders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class RecurringPaymentReminderListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            user_id = int(request.query_params.get("user_id"))
        except (TypeError, ValueError):
            return Response(
                {"success": False, "error": "El parámetro user_id es obligatorio y debe ser un número."},
                status=status.HTTP_400_BAD_REQUEST
            )

        day = request.query_params.get("day")
        month = request.query_params.get("month")
        year = request.query_params.get("year")

        result = get_recurring_payment_reminders(user_id, day, month, year)
        return Response(result, status=status.HTTP_200_OK)

class RecurringPaymentMarkPaidView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, reminder_id):
        try:
            reminder = RecurringPaymentReminder.objects.get(id=reminder_id)
        except RecurringPaymentReminder.DoesNotExist:
            return Response(
                {"success": False, "message": "Recordatorio no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Evita marcar dos veces el mismo día
        if reminder.last_payment_date == date.today():
            return Response(
                {"success": False, "message": "El pago ya fue marcado como realizado hoy."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Marcar como pagado hoy
        reminder.last_payment_date = date.today()
        reminder.save()

        return Response(
            {
                "success": True,
                "message": f"Pago de '{reminder.name}' marcado como realizado el {reminder.last_payment_date}.",
                "data": RecurringPaymentSerializer(reminder).data
            },
            status=status.HTTP_200_OK
        )


def get_recurring_payment_reminders(user_id: int, day=None, month=None, year=None):
    """
    Retorna los recordatorios que deben mostrarse para el usuario en una fecha dada.
    Esta función replica exactamente la lógica de RecurringPaymentReminderListView.get()
    para que pueda reutilizarse en otras vistas, como HomeDashboardView.
    """

    # Validar o usar fecha actual
    today = now().date()
    day = int(day) if day else today.day
    month = int(month) if month else today.month
    year = int(year) if year else today.year
    current_date = date(year, month, day)

    # 👇 Depuración
    print("📅 Fecha actual del sistema:", today)
    print("🧩 Parámetros recibidos → day:", day, "| month:", month, "| year:", year)
    print("🧾 Fecha generada → current_date:", current_date)

    # Obtener recordatorios activos
    reminders = RecurringPaymentReminder.objects.filter(
        user_id=user_id,
        is_active=True,
        start_date__lte=current_date
    )

    reminders_to_alert = []

    for reminder in reminders:
        # Construir la fecha de pago para el mes actual
        try:
            payment_date_this_month = date(year, month, reminder.payment_day)
        except ValueError:
            # Si el payment_day no existe en este mes (ej: día 31 en febrero)
            last_day = calendar.monthrange(year, month)[1]
            payment_date_this_month = date(year, month, last_day)

        # Si la fecha de pago ya pasó en este mes, usar el próximo mes
        if current_date > payment_date_this_month:
            next_month_date = payment_date_this_month + relativedelta(months=1)
            payment_date_to_check = next_month_date
            target_month = next_month_date.month
            target_year = next_month_date.year
        else:
            payment_date_to_check = payment_date_this_month
            target_month = month
            target_year = year

        # Verificar si ya fue pagado en el período objetivo
        if reminder.last_payment_date:
            if (reminder.last_payment_date.year == target_year and
                    reminder.last_payment_date.month == target_month):
                continue

        # Calcular rango de alertas (3 días antes, incluyendo el día)
        alert_start_date = payment_date_to_check - timedelta(days=2)
        alert_end_date = payment_date_to_check

        # Verificar si la fecha actual está en el rango de alerta
        if alert_start_date <= current_date <= alert_end_date:
            reminders_to_alert.append(reminder)

    # Serializar resultados
    serializer = RecurringPaymentSerializer(reminders_to_alert, many=True)

    return serializer.data