from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
import os
import tempfile
from moneymind_apps.movements.utils.services.gemini_api import analyze_expense, analyze_income

class ExpenseReceiptGeminiView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        image = request.FILES.get("file")
        if not image:
            return Response({"error": "No se envió ninguna imagen"}, status=400)

        # Guardar imagen temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            for chunk in image.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name

        try:
            result = analyze_expense(tmp_path)
            return Response({"data": result})
        finally:
            os.remove(tmp_path)

class IncomeReceiptGeminiView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        image = request.FILES.get("file")
        if not image:
            return Response({"error": "No se envió ninguna imagen"}, status=400)

        # Guardar imagen temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            for chunk in image.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name

        try:
            result = analyze_income(tmp_path)
            return Response({"data": result})
        finally:
            os.remove(tmp_path)