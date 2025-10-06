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