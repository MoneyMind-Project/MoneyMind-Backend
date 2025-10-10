from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from moneymind_apps.balances.models import *


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
