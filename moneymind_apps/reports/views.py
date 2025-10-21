from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from moneymind_apps.balances.models import *
from moneymind_apps.alerts.models import Alert, AlertType
from moneymind_apps.users.models import User
from django.utils import timezone
from moneymind_apps.reports.models import *
from moneymind_apps.movements.utils.services.gemini_api import *
from moneymind_apps.alerts.views import get_recurring_payment_reminders
import math


class DashboardOverviewView(APIView):
    permission_classes = [AllowAny]
    """
    Retorna los KPIs principales del dashboard
    """

    def get(self, request):
        user_id = request.query_params.get('user_id')
        month = request.query_params.get('month')
        year = request.query_params.get('year')

        if not user_id:
            return Response(
                {"error": "user_id es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if not month:
                month = datetime.now().month
            else:
                month = int(month)

            if not year:
                year = datetime.now().year
            else:
                year = int(year)

        except ValueError as e:
            return Response(
                {"error": f"Parámetros inválidos: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Total gastado este mes
        total_gastado = Expense.objects.filter(
            user_id=user_id,
            date__month=month,
            date__year=year
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')

        # 2. Categoría más alta
        categoria_alta = Expense.objects.filter(
            user_id=user_id,
            date__month=month,
            date__year=year
        ).values('category').annotate(
            total=Sum('total')
        ).order_by('-total').first()

        categoria_mas_alta = None
        if categoria_alta:
            from moneymind_apps.movements.models import CATEGORY_LABELS
            try:
                cat_enum = Category(categoria_alta['category'])
                categoria_mas_alta = {
                    "category": categoria_alta['category'],
                    "label": CATEGORY_LABELS.get(cat_enum, categoria_alta['category']),
                    "total": float(categoria_alta['total'])
                }
            except ValueError:
                categoria_mas_alta = None

        # 3. Presupuesto restante (balance actual)
        try:
            balance = Balance.objects.get(user_id=user_id)
            presupuesto_restante = float(balance.current_amount)
        except Balance.DoesNotExist:
            presupuesto_restante = 0

        # 👈 NUEVO: Calcular presupuesto inicial del mes
        # Presupuesto inicial = balance actual + total gastado este mes
        presupuesto_inicial_mes = presupuesto_restante + float(total_gastado)

        # 4. Proyección del próximo mes (promedio de últimos 3 meses)
        last_3_months_totals = []

        for i in range(1, 4):
            target_month = month - i
            target_year = year

            if target_month <= 0:
                target_month += 12
                target_year -= 1

            month_total = Expense.objects.filter(
                user_id=user_id,
                date__month=target_month,
                date__year=target_year
            ).aggregate(total=Sum('total'))['total'] or Decimal('0')

            last_3_months_totals.append(float(month_total))

        # 🔹 Lógica mejorada de proyección
        valid_months = [v for v in last_3_months_totals if v > 0]

        if len(valid_months) >= 2:
            # Promedio de los meses que sí tienen datos
            proyeccion = sum(valid_months) / len(valid_months)
        elif len(valid_months) == 1:
            # Si solo hay un mes, usa ese valor (lo repetimos virtualmente)
            proyeccion = valid_months[0]
        else:
            # Si no hay ningún dato previo, usa el gasto actual como referencia
            proyeccion = float(total_gastado)

        # 🔸 Redondear hacia arriba si tiene decimales
        proyeccion = math.ceil(proyeccion)

        # Verificar y crear alerta si es necesario
        # 👈 CAMBIO: Pasar presupuesto_inicial_mes en lugar de presupuesto_restante
        self.check_budget_alert(user_id, month, year, float(total_gastado), presupuesto_inicial_mes)

        return Response(
            {
                "success": True,
                "data": {
                    "total_gastado_mes": float(total_gastado),
                    "categoria_mas_alta": categoria_mas_alta,
                    "presupuesto_restante": presupuesto_restante,
                    "proyeccion_proximo_mes": round(proyeccion, 2)
                },
                "month": month,
                "year": year
            },
            status=status.HTTP_200_OK
        )

    def check_budget_alert(self, user_id, month, year, total_gastado, presupuesto_inicial_mes):
        """
        Verifica si se debe crear una alerta de presupuesto
        """
        # Calcular si se gastó más de 2/3 del presupuesto inicial del mes
        if presupuesto_inicial_mes > 0:
            umbral = presupuesto_inicial_mes * (2 / 3)

            if total_gastado >= umbral:
                # Verificar si ya existe una alerta para este mes
                alert_exists = Alert.objects.filter(
                    user_id=user_id,
                    alert_type=AlertType.RISK.value,
                    target_month=month,
                    target_year=year
                ).exists()

                if not alert_exists:
                    # Calcular cuánto queda del presupuesto inicial
                    restante = presupuesto_inicial_mes - total_gastado
                    porcentaje = (total_gastado / presupuesto_inicial_mes) * 100

                    Alert.objects.create(
                        user_id=user_id,
                        alert_type=AlertType.RISK.value,
                        message=f"Has gastado 2/3 de tu presupuesto inicial este mes (S/ {presupuesto_inicial_mes:.2f}).",
                        target_month=month,
                        target_year=year,
                        seen=False
                    )

class HomeDashboardView(APIView):
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

        # Obtener mes y año actuales
        now = timezone.now()
        current_month = now.month
        current_year = now.year

        # 2. Obtener tip semanal (temporal - datos inventados)
        weekly_tip = self._get_weekly_tip(int(user_id))

        # 3. Obtener datos de presupuesto
        budget_data = self._get_budget_data(user_id, current_month, current_year)

        # 4. Obtener gastos diarios del mes
        daily_expenses = self._get_daily_expenses(user_id, current_month, current_year)

        # 5. Obtener próximos pagos (reutilizando la lógica de alerts)
        upcoming_payments = get_recurring_payment_reminders(user_id)

        return Response(
            {
                "success": True,
                "data": {
                    "weekly_tip": weekly_tip,
                    "budget": budget_data,
                    "daily_expenses": daily_expenses,
                    "upcoming_payments": upcoming_payments
                }
            },
            status=status.HTTP_200_OK
        )

    def _get_weekly_tip(self, user_id: int):
        """Obtiene el tip semanal personalizado basado en IA"""
        try:
            tip_message = get_or_generate_weekly_tip(user_id)
            return {
                "title": "Consejo de la semana",
                "message": tip_message
            }
        except Exception as e:
            # Fallback en caso de error
            print(f"Error obteniendo weekly tip: {str(e)}")
            return {
                "title": "Consejo de ahorro",
                "message": "Revisa tus gastos semanalmente para mantener el control de tu presupuesto."
            }

    def _get_budget_data(self, user_id, month, year):
        """Calcular presupuesto del mes actual"""

        # Total gastado este mes
        total_gastado = Expense.objects.filter(
            user_id=user_id,
            date__month=month,
            date__year=year
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')

        # Presupuesto restante (balance actual)
        try:
            balance = Balance.objects.get(user_id=user_id)
            presupuesto_restante = float(balance.current_amount)
        except Balance.DoesNotExist:
            presupuesto_restante = 0

        # Total del presupuesto
        total_presupuesto = float(total_gastado) + presupuesto_restante

        # Calcular porcentaje gastado
        if total_presupuesto > 0:
            porcentaje_gastado = round((float(total_gastado) / total_presupuesto) * 100, 1)
        else:
            porcentaje_gastado = 0

        return {
            "month": month,  # Número del mes (1-12)
            "year": year,
            "total": round(total_presupuesto, 2),
            "spent": round(float(total_gastado), 2),
            "remaining": round(presupuesto_restante, 2),
            "percentage": porcentaje_gastado
        }

    def _get_daily_expenses(self, user_id, month, year):
        """
        Obtener gastos agrupados por día del mes actual
        Retorna array con {day, amount} para cada día que tuvo gastos
        """

        # Obtener todos los gastos del mes
        expenses = Expense.objects.filter(
            user_id=user_id,
            date__month=month,
            date__year=year
        ).values('date').annotate(
            total_amount=Sum('total')
        ).order_by('date')

        # Formatear datos para el gráfico
        daily_data = []
        for expense in expenses:
            daily_data.append({
                "day": expense['date'].day,
                "amount": round(float(expense['total_amount']), 2)
            })

        return daily_data

class MonthlyExpensesPredictionView(APIView):
    permission_classes = [AllowAny]
    """
    Obtiene gastos mensuales reales y predicciones para el resto del año
    """

    def get(self, request):
        user_id = request.query_params.get('user_id')
        year = request.query_params.get('year', None)

        if not user_id:
            return Response(
                {"error": "user_id es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if not year:
                from datetime import datetime
                year = datetime.now().year
            else:
                year = int(year)

        except ValueError as e:
            return Response(
                {"error": f"Parámetros inválidos: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        from datetime import datetime
        current_date = datetime.now()
        current_month = current_date.month if current_date.year == year else 12

        # Obtener gastos reales de cada mes
        monthly_expenses = []
        for month in range(1, 13):
            month_total = Expense.objects.filter(
                user_id=user_id,
                date__month=month,
                date__year=year
            ).aggregate(total=Sum('total'))['total']

            monthly_expenses.append({
                "month": month,
                "real": float(month_total) if month_total else None
            })

        # Calcular predicción para meses futuros
        months_with_data = [m for m in monthly_expenses if m["real"] is not None and m["real"] > 0]

        if len(months_with_data) >= 3:
            last_3_months = months_with_data[-3:]
            avg_expense = sum(m["real"] for m in last_3_months) / 3
        elif len(months_with_data) > 0:
            avg_expense = sum(m["real"] for m in months_with_data) / len(months_with_data)
        else:
            avg_expense = 0

        # Obtener el valor real del mes actual para usar como punto de partida
        current_month_value = monthly_expenses[current_month - 1]["real"] if current_month <= 12 else None

        predictions = []
        for i, month_data in enumerate(monthly_expenses):
            month = month_data["month"]

            if month < current_month:
                # Meses pasados - no hay predicción
                predictions.append(None)
            elif month == current_month:
                # Mes actual - usar valor real para conectar las líneas
                predictions.append(current_month_value)
            else:
                # Meses futuros - calcular predicción
                months_ahead = month - current_month
                # Usar el valor del mes actual como base
                base_value = current_month_value if current_month_value else avg_expense
                predicted_value = base_value * (1.02 ** months_ahead)
                predictions.append(round(predicted_value, 2))

        # Formatear respuesta
        result = []
        for i, month_data in enumerate(monthly_expenses):
            result.append({
                "month": month_data["month"],
                "real": month_data["real"],
                "prediction": predictions[i]
            })

        return Response(
            {
                "success": True,
                "data": result,
                "year": year,
                "current_month": current_month
            },
            status=status.HTTP_200_OK
        )

class ExpensesByCategoryView(APIView):
    permission_classes = [AllowAny]
    """
    Obtiene el total gastado por cada categoría en un mes específico
    """

    def get(self, request):
        user_id = request.query_params.get('user_id')
        month = request.query_params.get('month')  # Formato: número del 1-12
        year = request.query_params.get('year', None)  # Opcional, por defecto año actual

        if not user_id or not month:
            return Response(
                {"error": "user_id y month son requeridos"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            month = int(month)
            if month < 1 or month > 12:
                raise ValueError("Mes inválido")

            # Si no se proporciona year, usar el año actual
            if not year:
                from datetime import datetime
                year = datetime.now().year
            else:
                year = int(year)

        except ValueError as e:
            return Response(
                {"error": f"Parámetros inválidos: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Filtrar expenses por user, mes y año
        expenses = Expense.objects.filter(
            user_id=user_id,
            date__month=month,
            date__year=year
        )

        # Agrupar por categoría y sumar totales
        category_totals = expenses.values('category').annotate(
            total=Sum('total')
        )

        # Crear un diccionario con todas las categorías inicializadas en 0
        all_categories = {cat.value: 0 for cat in Category}

        # Actualizar con los totales reales
        for item in category_totals:
            all_categories[item['category']] = float(item['total'])

        # Formatear respuesta con todas las categorías
        result = [
            {
                "category": category,
                "total": total
            }
            for category, total in all_categories.items()
        ]

        return Response(
            {
                "success": True,
                "data": result,
                "month": month,
                "year": year
            },
            status=status.HTTP_200_OK
        )

class ExpensesByParentCategoryView(APIView):
    permission_classes = [AllowAny]
    """
    Obtiene el total gastado por cada categoría padre en un mes específico
    """

    def get(self, request):
        user_id = request.query_params.get('user_id')
        month = request.query_params.get('month')
        year = request.query_params.get('year', None)

        if not user_id or not month:
            return Response(
                {"error": "user_id y month son requeridos"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            month = int(month)
            if month < 1 or month > 12:
                raise ValueError("Mes inválido")

            if not year:
                from datetime import datetime
                year = datetime.now().year
            else:
                year = int(year)

        except ValueError as e:
            return Response(
                {"error": f"Parámetros inválidos: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Filtrar expenses por user, mes y año
        expenses = Expense.objects.filter(
            user_id=user_id,
            date__month=month,
            date__year=year
        )

        # Inicializar totales por categoría padre en 0
        parent_totals = {parent.value: 0 for parent in CategoryParent}

        # Sumar gastos por cada expense
        for expense in expenses:
            try:
                # Obtener la categoría del expense
                category = Category(expense.category)
                # Obtener la categoría padre correspondiente
                parent_category = CATEGORY_PARENT_MAP.get(category)

                if parent_category:
                    parent_totals[parent_category.value] += float(expense.total)

            except ValueError:
                # Si la categoría no es válida, continuar
                continue

        # Formatear respuesta
        result = [
            {
                "parent_category": parent_category,
                "total": total
            }
            for parent_category, total in parent_totals.items()
        ]

        return Response(
            {
                "success": True,
                "data": result,
                "month": month,
                "year": year
            },
            status=status.HTTP_200_OK
        )

class SavingsEvolutionView(APIView):
    permission_classes = [AllowAny]
    """
    Obtiene la evolución del ahorro mes a mes
    """

    def get(self, request):
        user_id = request.query_params.get('user_id')
        year = request.query_params.get('year', None)

        if not user_id:
            return Response(
                {"error": "user_id es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if not year:
                from datetime import datetime
                year = datetime.now().year
            else:
                year = int(year)

        except ValueError as e:
            return Response(
                {"error": f"Parámetros inválidos: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        from moneymind_apps.balances.models import UserBalanceHistory

        # Obtener el historial de balances del año
        history = UserBalanceHistory.objects.filter(
            user_id=user_id,
            date__year=year
        ).order_by('date')

        # Formatear respuesta
        monthly_savings = []
        previous_amount = None

        for record in history:
            # Calcular el ahorro (diferencia con el mes anterior)
            if previous_amount is not None:
                saving = float(record.amount) - previous_amount
            else:
                saving = 0  # Primer mes no tiene comparación

            monthly_savings.append({
                "month": record.date.month,
                "date": record.date.isoformat(),
                "balance": float(record.amount),
                "saving": saving
            })

            previous_amount = float(record.amount)

        return Response(
            {
                "success": True,
                "data": monthly_savings,
                "year": year
            },
            status=status.HTTP_200_OK
        )

class EssentialVsNonEssentialExpensesView(APIView):
    permission_classes = [AllowAny]
    """
    Obtiene gastos esenciales vs no esenciales por mes durante un año específico
    """

    def get(self, request):
        user_id = request.query_params.get('user_id')
        year = request.query_params.get('year', None)

        if not user_id:
            return Response(
                {"error": "user_id es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if not year:
                from datetime import datetime
                year = datetime.now().year
            else:
                year = int(year)

        except ValueError as e:
            return Response(
                {"error": f"Parámetros inválidos: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        from moneymind_apps.movements.models import ExpenseType, CATEGORY_EXPENSE_TYPE_MAP

        # Resultado por cada mes
        monthly_data = []

        for month in range(1, 13):  # Meses del 1 al 12
            # Filtrar expenses del mes
            expenses = Expense.objects.filter(
                user_id=user_id,
                date__month=month,
                date__year=year
            )

            esencial_total = 0
            no_esencial_total = 0

            # Clasificar y sumar
            for expense in expenses:
                try:
                    category = Category(expense.category)
                    expense_type = CATEGORY_EXPENSE_TYPE_MAP.get(category)

                    if expense_type == ExpenseType.ESENCIAL:
                        esencial_total += float(expense.total)
                    elif expense_type == ExpenseType.NO_ESENCIAL:
                        no_esencial_total += float(expense.total)

                except ValueError:
                    continue

            monthly_data.append({
                "month": month,
                "esencial": esencial_total,
                "no_esencial": no_esencial_total
            })

        return Response(
            {
                "success": True,
                "data": monthly_data,
                "year": year
            },
            status=status.HTTP_200_OK
        )


def get_or_generate_weekly_tip(user_id: int) -> str:
    """
    Obtiene el tip semanal del usuario o genera uno nuevo si no existe o está vencido
    """
    try:
        tip_obj = WeeklyTip.objects.get(user_id=user_id)

        # Si el tip tiene más de 7 días, regenerar
        if tip_obj.should_regenerate():
            new_tip = generate_weekly_tip(user_id)
            tip_obj.tip = new_tip
            tip_obj.created_at = datetime.now()
            tip_obj.save()
            return new_tip

        return tip_obj.tip

    except WeeklyTip.DoesNotExist:
        # No existe, crear uno nuevo
        new_tip = generate_weekly_tip(user_id)
        WeeklyTip.objects.create(user_id=user_id, tip=new_tip)
        return new_tip