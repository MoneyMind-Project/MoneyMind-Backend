from django.urls import path
from .views import ExpenseReceiptGeminiView, IncomeReceiptGeminiView

urlpatterns = [
    path("analyze-expense/", ExpenseReceiptGeminiView.as_view(), name="receipt-analyze"),
    path("analyze-income/", IncomeReceiptGeminiView.as_view(), name="receipt-analyze"),
]