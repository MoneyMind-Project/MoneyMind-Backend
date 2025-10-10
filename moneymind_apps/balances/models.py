from django.db import models
from django.conf import settings

class Balance(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="balance"
    )
    current_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        null=False,
        blank=False,   # obligatorio, siempre debe venir en el registro
    )
    monthly_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,    # opcional, el usuario puede decidir no ponerlo
    )

    class Meta:
        db_table = "balances"

    def __str__(self):
        return f"Balance de {self.user.email}: {self.current_amount}"


class UserBalanceHistory(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="balance_history"
    )
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "user_balance_history"
        unique_together = ['user', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} - {self.date} - S/ {self.amount}"