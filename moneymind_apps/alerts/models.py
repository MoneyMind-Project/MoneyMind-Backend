from django.db import models
from django.conf import settings
from enum import Enum
from moneymind_apps.movements.models import *

class AlertType(Enum):
    RISK = "risk"
    REMINDER = "reminder"

class Alert(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="alerts"
    )
    alert_type = models.CharField(
        max_length=20,
        choices=[(tag.value, tag.value) for tag in AlertType]
    )
    message = models.TextField()
    target_month = models.IntegerField()  # Mes al que apunta (1-12)
    target_year = models.IntegerField()   # Año al que apunta
    seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "alerts"
        ordering = ["-created_at"]
        # Evitar alertas duplicadas para el mismo mes/año/tipo
        unique_together = ['user', 'alert_type', 'target_month', 'target_year']

    def __str__(self):
        return f"{self.alert_type} - {self.user.username} - {self.target_month}/{self.target_year}"


class RecurringPaymentReminder(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recurring_payments"
    )
    name = models.CharField(max_length=255)  # "Netflix Premium", "Internet Movistar"
    category = models.CharField(
        max_length=50,
        choices=[(tag.value, tag.value) for tag in Category]
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Monto mensual/periódico

    # Recurrencia
    recurrence_type = models.CharField(max_length=20, default='monthly')
    payment_day = models.IntegerField()  # Día del mes (1-31)

    # Estado
    is_active = models.BooleanField(default=True)  # Si sigue activo o ya se canceló
    start_date = models.DateField()  # Desde cuándo empezó
    end_date = models.DateField(null=True, blank=True)  # Si es que tiene fecha de fin (deudas con plazo)

    # NUEVOS CAMPOS PARA MANEJAR LA ALERTA
    last_payment_date = models.DateField(null=True, blank=True)  # Última fecha en que se marcó como pagado

    created_at = models.DateTimeField(auto_now_add=True)

    def mark_as_paid_for_month(self, year, month):
        """Marca este recordatorio como pagado para un mes específico"""
        from datetime import datetime
        self.last_payment_date = datetime.now().date()
        self.save()

    def should_show_alert(self, target_month, target_year):
        """
        Verifica si debe mostrar la alerta para este mes
        """
        # debe mostrarse si last_payment_date es mas viejo que el mes actual y estoy en el rango de 3 dias antes del pago incluyendo el mismo dia
        if not self.last_alert_month or not self.last_alert_year:
            return True

        return False

    class Meta:
        db_table = "recurring_payments_reminder"
        ordering = ['start_date']

    def __str__(self):
        return f"{self.name} - S/ {self.amount}"
