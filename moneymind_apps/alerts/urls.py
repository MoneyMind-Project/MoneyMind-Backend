from django.urls import path
from .views import *

urlpatterns = [
    path('user-alerts/', UserAlertsView.as_view(), name='user-alerts'),
    path('user-alerts-pagination/', UserAlertsPaginationView.as_view(), name='user-alerts-pagination'),
    path('mark-seen/<int:user_id>/<int:alert_id>/', MarkAlertAsSeenView.as_view(), name='mark_alert_as_seen'),
    path('mark-all-risk-seen/<int:user_id>/', MarkAllRiskAlertsAsSeenView.as_view(), name='mark-all-risk-seen'),
]
