from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.db.models import Sum
from decimal import Decimal
from moneymind_apps.movements.models import *


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