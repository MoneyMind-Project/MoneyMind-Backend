from django.urls import path
from .views import ReceiptCloudView, ReceiptGeminiView

urlpatterns = [
    path('upload/', ReceiptCloudView.as_view(), name='receipt-upload'),
    path("analyze/", ReceiptGeminiView.as_view(), name="receipt-analyze"),
]