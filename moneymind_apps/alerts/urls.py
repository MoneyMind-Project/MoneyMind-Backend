from django.urls import path
from .views import *

urlpatterns = [
    path('user-alerts/', UserAlertsView.as_view(), name='user-alerts'),
    path('user-alerts-pagination/', UserAlertsPaginationView.as_view(), name='user-alerts-pagination'),
]
