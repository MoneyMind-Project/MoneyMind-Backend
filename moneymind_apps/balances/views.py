from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from moneymind_apps.balances.models import *
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from moneymind_apps.users.models import *

def update_monthly_income(user_id, new_income):
    try:
        balance, created = Balance.objects.get_or_create(user_id=user_id)
        balance.monthly_income = new_income
        balance.save()
        return balance
    except Exception as e:
        raise ValueError(f"Error al actualizar monthly_income: {str(e)}")

def check_and_register_monthly_balance(user_id):
    """
    Verifica si el balance del mes anterior está registrado.
    Si no existe, lo registra automáticamente.
    """
    current_date = date.today()

    # Calcular el último día del mes anterior
    first_day_current_month = current_date.replace(day=1)
    last_day_previous_month = first_day_current_month - relativedelta(days=1)

    # Verificar si ya existe el registro del mes anterior
    balance_exists = UserBalanceHistory.objects.filter(
        user_id=user_id,
        date=last_day_previous_month
    ).exists()

    if not balance_exists:
        # Obtener el balance actual del usuario
        try:
            balance = Balance.objects.get(user_id=user_id)

            # Crear el registro histórico del mes anterior
            UserBalanceHistory.objects.create(
                user_id=user_id,
                date=last_day_previous_month,
                amount=balance.current_amount
            )

            print(f"✓ Balance histórico registrado para {last_day_previous_month}: S/ {balance.current_amount}")

        except Balance.DoesNotExist:
            print(f"✗ Usuario {user_id} no tiene balance configurado")

class UpdateMonthlyIncomeView(APIView):
    permission_classes = [AllowAny]

    def patch(self, request):
        user_id = request.data.get('user_id')
        new_monthly_income = request.data.get('new_monthly_income')

        # 1️⃣ Validar parámetros
        if not user_id:
            return Response(
                {"error": "user_id es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_monthly_income is None:
            return Response(
                {"error": "new_monthly_income es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2️⃣ Verificar que el usuario exista
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "Usuario no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3️⃣ Buscar el balance del usuario
        try:
            balance = Balance.objects.get(user_id=user_id)
        except Balance.DoesNotExist:
            return Response(
                {"error": "No se encontró el balance para este usuario"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 4️⃣ Actualizar el monthly_income
        try:
            balance.monthly_income = Decimal(new_monthly_income)
            balance.save()

            return Response(
                {
                    "success": True,
                    "message": "Ingreso mensual actualizado correctamente",
                    "data": {
                        "user_id": user_id,
                        "monthly_income": str(balance.monthly_income)
                    }
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": f"Ocurrió un error al actualizar el ingreso mensual: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GetUserBalanceView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user_id = request.query_params.get('user_id')

        if not user_id:
            return Response(
                {"error": "user_id es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "Usuario no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            balance = Balance.objects.get(user=user)
        except Balance.DoesNotExist:
            return Response(
                {"error": "Balance no encontrado para este usuario"},
                status=status.HTTP_404_NOT_FOUND
            )

        # ✅ Devolver ambos valores: ingreso mensual y balance actual
        return Response(
            {
                "user_id": user.id,
                "monthly_income": balance.monthly_income,
                "current_balance": balance.current_amount
            },
            status=status.HTTP_200_OK
        )