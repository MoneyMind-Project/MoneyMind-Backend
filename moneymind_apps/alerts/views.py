from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from moneymind_apps.alerts.models import *
from django.shortcuts import get_object_or_404
from moneymind_apps.alerts.serializer import *
from django.utils.timezone import now
from datetime import date

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


class RecurringPaymentReminderListView(APIView):
    """
    Retorna los recordatorios que deben mostrarse para el usuario en una fecha dada.
    Se muestran si:
      - El recordatorio está activo.
      - La fecha actual está dentro de los 3 días previos (incluyendo el día exacto) al día de pago.
      - No ha sido marcado como pagado este mes.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # Obtener parámetros obligatorios
        try:
            user_id = int(request.query_params.get("user_id"))
        except (TypeError, ValueError):
            return Response(
                {"success": False, "error": "El parámetro user_id es obligatorio y debe ser un número."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Obtener fecha desde los parámetros, si no se mandan usar hoy
        try:
            day = int(request.query_params.get("day", now().date().day))
            month = int(request.query_params.get("month", now().date().month))
            year = int(request.query_params.get("year", now().date().year))
            current_date = date(year, month, day)
        except ValueError:
            return Response(
                {"success": False, "error": "Los parámetros de fecha son inválidos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        reminders = RecurringPaymentReminder.objects.filter(
            user_id=user_id,
            is_active=True
        )

        reminders_to_alert = []
        for reminder in reminders:
            # Saltar si ya fue pagado este mes
            if reminder.last_payment_date and reminder.last_payment_date.month == month and reminder.last_payment_date.year == year:
                continue

            # Calcular rango de alerta (3 días antes del día de pago)
            alert_start = reminder.payment_day - 3
            if alert_start < 1:
                alert_start = 1

            if alert_start <= day <= reminder.payment_day:
                reminders_to_alert.append(reminder)

        serializer = RecurringPaymentSerializer(reminders_to_alert, many=True)

        return Response(
            {
                "success": True,
                "count": len(reminders_to_alert),
                "date_checked": current_date.strftime("%Y-%m-%d"),
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

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