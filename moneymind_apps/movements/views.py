from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.shortcuts import get_object_or_404
import os
import tempfile
from moneymind_apps.movements.utils.services.gemini_api import analyze_expense, analyze_income
from django.contrib.auth import get_user_model
from django.db.models import Q
from moneymind_apps.balances.models import Balance
from .serializers import ExpenseSerializer, IncomeSerializer
from decimal import Decimal
from moneymind_apps.movements.models import Expense, Income
from itertools import chain
from operator import attrgetter


User = get_user_model()  # Obtiene tu modelo User personalizado


class ExpenseReceiptGeminiView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        image = request.FILES.get("file")
        if not image:
            return Response(
                {"message": "No se envió ninguna imagen", "code": "NO_IMAGE"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Guardar imagen temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            for chunk in image.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name

        try:
            result = analyze_expense(tmp_path)

            # Si hay un error de validación
            if "error" in result:
                return Response(
                    {
                        "message": result["error"],
                        "code": result.get("code", "ANALYSIS_ERROR")
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Si el análisis fue exitoso
            return Response({"data": result}, status=status.HTTP_200_OK)

        finally:
            os.remove(tmp_path)


class IncomeReceiptGeminiView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        image = request.FILES.get("file")
        if not image:
            return Response(
                {"message": "No se envió ninguna imagen", "code": "NO_IMAGE"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Guardar imagen temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            for chunk in image.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name

        try:
            result = analyze_income(tmp_path)

            # Si hay un error de validación
            if "error" in result:
                return Response(
                    {
                        "message": result["error"],
                        "code": result.get("code", "ANALYSIS_ERROR")
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Si el análisis fue exitoso
            return Response({"data": result}, status=status.HTTP_200_OK)

        finally:
            os.remove(tmp_path)

class ExpenseCreateView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        serializer = ExpenseSerializer(data=request.data)

        if serializer.is_valid():
            # 👇 Aquí usamos el user_id directamente
            user_id = serializer.validated_data["user_id"]
            category = serializer.validated_data["category"]
            place = serializer.validated_data["place"]
            date = serializer.validated_data["date"]
            time = serializer.validated_data["time"]
            total = serializer.validated_data["total"]

            # 🔎 Verificar duplicado
            exists = Expense.objects.filter(
                user_id=user_id,
                category=category,
                place=place,
                date=date,
                time=time,
                total=total
            ).exists()

            if exists:
                return Response(
                    {"message": "DUPLICATED"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 👇 Usamos serializer.save() que internamente resuelve el user_id → user
            expense = serializer.save()
            balance = expense.user.balance
            balance.current_amount -= Decimal(expense.total)
            balance.save()

            return Response(
                {
                    "message": "Gasto registrado exitosamente",
                    "expense": ExpenseSerializer(expense).data,
                    "new_balance": str(balance.current_amount),
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
            user_id = serializer.validated_data["user_id"]
            title = serializer.validated_data["title"]
            date = serializer.validated_data["date"]
            time = serializer.validated_data["time"]
            total = serializer.validated_data["total"]

            # 🔎 Verificar duplicado
            exists = Income.objects.filter(
                user_id=user_id,
                title=title,
                date=date,
                time=time,
                total=total
            ).exists()

            if exists:
                return Response(
                    {"message": "DUPLICATED"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Crear el income normalmente (serializer se encarga de mapear user_id → user)
            income = serializer.save()

            balance = income.user.balance  # ✅ Aquí ya tenemos el user correcto
            balance.current_amount += Decimal(income.total)
            balance.save()

            return Response(
                {
                    "message": "Ingreso registrado exitosamente",
                    "income": IncomeSerializer(income).data,
                    "new_balance": str(balance.current_amount),
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


class ScanDashboardView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, user_id, *args, **kwargs):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "Usuario no encontrado"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Obtener balance actual
        try:
            balance = user.balance
            current_amount = str(balance.current_amount)
        except Balance.DoesNotExist:
            return Response(
                {"error": "El usuario no tiene un balance asociado"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Obtener últimos 10 incomes
        recent_incomes = Income.objects.filter(user=user).order_by('-date', '-time')[:10]

        # Obtener últimos 10 expenses
        recent_expenses = Expense.objects.filter(user=user).order_by('-date', '-time')[:10]

        # Combinar y ordenar por fecha y hora (últimos 10 en total)
        combined_movements = list(chain(recent_incomes, recent_expenses))
        combined_movements.sort(key=attrgetter('date', 'time'), reverse=True)
        recent_movements = combined_movements[:10]

        # Serializar movimientos
        movements_data = []
        for movement in recent_movements:
            if isinstance(movement, Income):
                serializer = IncomeSerializer(movement)
                movement_data = serializer.data
                movement_data['type'] = 'income'
            else:  # Expense
                serializer = ExpenseSerializer(movement)
                movement_data = serializer.data
                movement_data['type'] = 'expense'

            movements_data.append(movement_data)

        return Response(
            {
                "current_balance": current_amount,
                "recent_movements": movements_data,
                "total_movements": len(movements_data)
            },
            status=status.HTTP_200_OK
        )


class AllMovementsOptimizedView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, user_id, *args, **kwargs):
        # Obtener parámetros de paginación
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))

        if page < 1 or page_size < 1:
            return Response(
                {"error": "Los parámetros page y page_size deben ser >= 1"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "Usuario no encontrado"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Obtener movimientos (ordenados descendente por fecha y hora)
        all_incomes = Income.objects.filter(user=user).order_by('-date', '-time')
        all_expenses = Expense.objects.filter(user=user).order_by('-date', '-time')

        combined_movements = list(chain(all_incomes, all_expenses))
        combined_movements.sort(key=attrgetter('date', 'time'), reverse=True)

        # Calcular offset y límite
        offset = (page - 1) * page_size
        movements_slice = combined_movements[offset:offset + page_size]

        # Serializar
        movements_data = []
        for movement in movements_slice:
            if isinstance(movement, Income):
                serializer = IncomeSerializer(movement)
                movement_data = serializer.data
                movement_data['type'] = 'income'
            else:
                serializer = ExpenseSerializer(movement)
                movement_data = serializer.data
                movement_data['type'] = 'expense'
            movements_data.append(movement_data)

        # Calcular si hay más
        total_count = len(combined_movements)
        has_more = (offset + page_size) < total_count

        return Response(
            {
                "movements": movements_data,
                "has_more": has_more,
                "page": page,
                "page_size": page_size,
                "total_movements": total_count,
                "loaded_count": len(movements_data),
                "next_page": page + 1 if has_more else None
            },
            status=status.HTTP_200_OK
        )