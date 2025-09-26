from django.urls import path
from .views import *

urlpatterns = [
    path("analyze-expense/", ExpenseReceiptGeminiView.as_view(), name="receipt-analyze-expense"),
    path("analyze-income/", IncomeReceiptGeminiView.as_view(), name="receipt-analyze-income"),
    path("expense/create/", ExpenseCreateView.as_view(), name="expense-create"),
    path("income/create/", IncomeCreateView.as_view(), name="income-create"),
    path('income/delete/<int:pk>/', IncomeDeleteView.as_view(), name='income-delete'),
    path('expense/delete/<int:pk>/', ExpenseDeleteView.as_view(), name='expense-delete'),
    path('scan/dashboard/<int:user_id>/', ScanDashboardView.as_view(), name='scan-dashboard'),
    path('scan/all/<int:user_id>/', AllMovementsOptimizedView.as_view(), name='all-movements-optimized'),



]
