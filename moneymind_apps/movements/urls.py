from django.urls import path
from .views import (
    ExpenseReceiptGeminiView,
    IncomeReceiptGeminiView,
    ExpenseCreateView,
)

urlpatterns = [
    path("analyze-expense/", ExpenseReceiptGeminiView.as_view(), name="receipt-analyze-expense"),
    path("analyze-income/", IncomeReceiptGeminiView.as_view(), name="receipt-analyze-income"),
    path("expense/create/", ExpenseCreateView.as_view(), name="expense-create"),
]
