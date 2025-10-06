from django.urls import path
from .views import *

urlpatterns = [
    path('user-alerts/', UserAlertsView.as_view(), name='user-alerts'),
]
