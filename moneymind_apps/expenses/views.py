from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
import os
import tempfile
from moneymind_apps.expenses.utils.services.gemini_api import analizar_recibo

class ReceiptGeminiView(APIView):
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
            result = analizar_recibo(tmp_path)
            return Response({"data": result})
        finally:
            os.remove(tmp_path)