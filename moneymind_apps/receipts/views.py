from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import tempfile
from .utils.services.ocr_service import extract_text_from_image
from .utils.services.gemini_api import analizar_recibo

class ReceiptCloudView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        file = request.FILES.get("file")

        if not file:
            return Response({"error": "No se envió archivo"}, status=400)

        # Guardar temporalmente
        file_path = default_storage.save(
            "uploads/" + file.name,
            ContentFile(file.read())
        )
        abs_path = os.path.join(default_storage.location, file_path)

        try:
            # Pasar la imagen al servicio OCR
            extracted_text = extract_text_from_image(abs_path)

            return Response({
                "message": "Imagen procesada correctamente",
                "text": extracted_text
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)

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