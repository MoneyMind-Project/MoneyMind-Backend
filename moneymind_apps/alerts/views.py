from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.db.models import Sum
from django.http import HttpResponse
from moneymind_apps.alerts.models import *

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