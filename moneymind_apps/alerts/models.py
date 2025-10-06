from django.db import models
from django.conf import settings
from enum import Enum

class AlertType(Enum):
    RISK = "risk"
    RECOMMENDATION = "recommendation"

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