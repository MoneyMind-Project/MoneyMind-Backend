from django.urls import path
from .views import *

urlpatterns = [
    path('user-balance/', GetUserBalanceView.as_view(), name='get-user-balance'),
    path('update-monthly-income/', UpdateMonthlyIncomeView.as_view(), name='update-monthly-income'),
]


