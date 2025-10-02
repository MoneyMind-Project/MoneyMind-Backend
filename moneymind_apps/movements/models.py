from django.db import models
from django.conf import settings
from enum import Enum


class CategoryParent(Enum):
    GASTOS_ESENCIALES = "gastos_esenciales"
    GASTOS_PERSONALES = "gastos_personales"
    FINANCIEROS = "financieros"
    EDUCACION = "educacion"
    OTROS = "otros"


class Category(Enum):
    # GASTOS_ESENCIALES
    VIVIENDA = "vivienda"
    SERVICIOS_BASICOS = "servicios_basicos"
    ALIMENTACION = "alimentacion"
    TRANSPORTE = "transporte"
    SALUD = "salud"

    # GASTOS_PERSONALES
    ENTRETENIMIENTO = "entretenimiento"
    STREAMING_SUSCRIPCIONES = "streaming_suscripciones"
    MASCOTAS = "mascotas"
    CUIDADO_PERSONAL = "cuidado_personal"

    # FINANCIEROS
    DEUDAS_PRESTAMOS = "deudas_prestamos"
    AHORRO_INVERSION = "ahorro_inversion"
    SEGUROS = "seguros"

    # EDUCACION
    EDUCACION_DESARROLLO = "educacion_desarrollo"

    # OTROS
    REGALOS_CELEBRACIONES = "regalos_celebraciones"
    VIAJES_VACACIONES = "viajes_vacaciones"
    IMPREVISTOS = "imprevistos"


# Mapeo de categorías a sus padres
CATEGORY_PARENT_MAP = {
    Category.VIVIENDA: CategoryParent.GASTOS_ESENCIALES,
    Category.SERVICIOS_BASICOS: CategoryParent.GASTOS_ESENCIALES,
    Category.ALIMENTACION: CategoryParent.GASTOS_ESENCIALES,
    Category.TRANSPORTE: CategoryParent.GASTOS_ESENCIALES,
    Category.SALUD: CategoryParent.GASTOS_ESENCIALES,

    Category.ENTRETENIMIENTO: CategoryParent.GASTOS_PERSONALES,
    Category.STREAMING_SUSCRIPCIONES: CategoryParent.GASTOS_PERSONALES,
    Category.MASCOTAS: CategoryParent.GASTOS_PERSONALES,
    Category.CUIDADO_PERSONAL: CategoryParent.GASTOS_PERSONALES,

    Category.DEUDAS_PRESTAMOS: CategoryParent.FINANCIEROS,
    Category.AHORRO_INVERSION: CategoryParent.FINANCIEROS,
    Category.SEGUROS: CategoryParent.FINANCIEROS,

    Category.EDUCACION_DESARROLLO: CategoryParent.EDUCACION,

    Category.REGALOS_CELEBRACIONES: CategoryParent.OTROS,
    Category.VIAJES_VACACIONES: CategoryParent.OTROS,
    Category.IMPREVISTOS: CategoryParent.OTROS,
}


def get_parent_category(category: Category) -> CategoryParent:
    """Obtiene la categoría padre de una categoría específica"""
    return CATEGORY_PARENT_MAP.get(category)


class Expense(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="expenses"
    )
    category = models.CharField(
        max_length=50,
        choices=[(tag.value, tag.value) for tag in Category]
    )
    place = models.CharField(max_length=255)
    date = models.DateField()
    time = models.TimeField()
    total = models.DecimalField(max_digits=10, decimal_places=2)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "expenses"
        ordering = ["-date", "-time"]

    def __str__(self):
        return f"{self.place} - {self.total} ({self.date})"

class Income(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="incomes"
    )
    title = models.CharField(max_length=255)
    date = models.DateField()
    time = models.TimeField()
    total = models.DecimalField(max_digits=10, decimal_places=2)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "incomes"
        ordering = ["-date", "-time"]

    def __str__(self):
        return f"{self.title} - {self.total} ({self.date})"