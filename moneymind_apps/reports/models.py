from django.db import models
from django.conf import settings
from enum import Enum

class WeeklyTip(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    tip = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "weekly_tips"

    def __str__(self):
        return f"Tip for {self.user.username} - {self.created_at.date()}"

    def should_regenerate(self):
        """Verifica si el tip tiene más de 7 días"""
        from datetime import datetime, timedelta
        return datetime.now() - self.created_at.replace(tzinfo=None) > timedelta(days=7)
