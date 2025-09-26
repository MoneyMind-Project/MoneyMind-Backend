from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status, permissions
import os
import tempfile
from moneymind_apps.movements.utils.services.gemini_api import analyze_expense, analyze_income
from .models import Expense
from moneymind_apps.balances.models import Balance
from .serializers import ExpenseSerializer
from decimal import Decimal

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

class ExpenseCreateView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # ← AGREGAR ESTA LÍNEA para deshabilitar autenticación

    def post(self, request, *args, **kwargs):
        print(">>> POST recibido en ExpenseCreateView", flush=True)
        print(f">>> Data recibida: {request.data}", flush=True)
        print(f">>> Headers: {request.headers}", flush=True)  # ← Ver headers

        serializer = ExpenseSerializer(data=request.data)

        if serializer.is_valid():
            print(">>> Serializer válido", flush=True)
            expense = serializer.save()
            print(f">>> Expense creado: {expense}", flush=True)
            print(f">>> Expense.user: {expense.user}", flush=True)

            user = expense.user

            try:
                balance = user.balance
                print(f">>> Balance encontrado: {balance.current_amount}", flush=True)
            except Balance.DoesNotExist:
                print(">>> ERROR: El usuario no tiene balance asociado", flush=True)
                return Response(
                    {"error": "El usuario no tiene un balance asociado"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            balance.current_amount = balance.current_amount - Decimal(expense.total)
            balance.save()
            print(f">>> Balance actualizado: {balance.current_amount}", flush=True)

            return Response(
                {
                    "message": "Gasto registrado exitosamente",
                    "expense": ExpenseSerializer(expense).data,
                    "new_balance": str(balance.current_amount)
                },
                status=status.HTTP_201_CREATED
            )

        print(f">>> Serializer inválido: {serializer.errors}", flush=True)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)