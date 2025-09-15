from django.urls import path
from .views import ReceiptGeminiView

urlpatterns = [
    path("analyze/", ReceiptGeminiView.as_view(), name="receipt-analyze"),
]