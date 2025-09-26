from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.shortcuts import get_object_or_404
import os
import tempfile
from moneymind_apps.movements.utils.services.gemini_api import analyze_expense, analyze_income
from moneymind_apps.balances.models import Balance
from .serializers import ExpenseSerializer, IncomeSerializer
from decimal import Decimal
from moneymind_apps.movements.models import Expense, Income

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

        serializer = ExpenseSerializer(data=request.data)

        if serializer.is_valid():
            expense = serializer.save()

            user = expense.user

            try:
                balance = user.balance
            except Balance.DoesNotExist:
                return Response(
                    {"error": "El usuario no tiene un balance asociado"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            balance.current_amount = balance.current_amount - Decimal(expense.total)
            balance.save()

            return Response(
                {
                    "message": "Gasto registrado exitosamente",
                    "expense": ExpenseSerializer(expense).data,
                    "new_balance": str(balance.current_amount)
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class IncomeCreateView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):

        serializer = IncomeSerializer(data=request.data)

        if serializer.is_valid():
            income = serializer.save()

            # Obtener el usuario del income recién creado
            user = income.user

            try:
                balance = user.balance
            except Balance.DoesNotExist:
                return Response(
                    {"error": "El usuario no tiene un balance asociado"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # SUMA el ingreso al current_amount (diferente a expense que resta)
            balance.current_amount = balance.current_amount + Decimal(income.total)
            balance.save()

            return Response(
                {
                    "message": "Ingreso registrado exitosamente",
                    "income": IncomeSerializer(income).data,
                    "new_balance": str(balance.current_amount)
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IncomeDeleteView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def delete(self, request, pk, *args, **kwargs):
        # Obtener el income o devolver 404 si no existe
        income = get_object_or_404(Income, id=pk)

        user = income.user
        income_amount = income.total

        try:
            balance = user.balance
        except Balance.DoesNotExist:
            return Response(
                {"error": "El usuario no tiene un balance asociado"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # RESTAR el monto del income del balance (porque se elimina un ingreso)
        balance.current_amount = balance.current_amount - Decimal(income_amount)
        balance.save()

        # Eliminar el income
        income.delete()

        return Response(
            {
                "message": "Ingreso eliminado exitosamente",
                "deleted_income_amount": str(income_amount),
                "new_balance": str(balance.current_amount)
            },
            status=status.HTTP_200_OK
        )


class ExpenseDeleteView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def delete(self, request, pk, *args, **kwargs):
        # Obtener el expense o devolver 404 si no existe
        expense = get_object_or_404(Expense, id=pk)

        user = expense.user
        expense_amount = expense.total

        try:
            balance = user.balance
        except Balance.DoesNotExist:
            return Response(
                {"error": "El usuario no tiene un balance asociado"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # SUMAR el monto del expense al balance (porque se elimina un gasto)
        balance.current_amount = balance.current_amount + Decimal(expense_amount)
        balance.save()

        # Eliminar el expense
        expense.delete()

        return Response(
            {
                "message": "Gasto eliminado exitosamente",
                "deleted_expense_amount": str(expense_amount),
                "new_balance": str(balance.current_amount)
            },
            status=status.HTTP_200_OK
        )
