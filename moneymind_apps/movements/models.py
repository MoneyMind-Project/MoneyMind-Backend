from django.db import models
import uuid
from django.conf import settings
from enum import Enum


class Category(Enum):
    ENTERTAINMENT = "entertainment"
    FOOD = "food"
    TRANSPORT = "transport"
    HOUSING = "housing"
    HEALTH = "health"
    SHOPPING = "shopping"
    UTILITIES = "utilities"
    OTHER = "other"


class Expense(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="movements"
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

    class Meta:
        db_table = "movements"
        ordering = ["-date", "-time"]

    def __str__(self):
        return f"{self.place} - {self.total} ({self.date})"

class Income(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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

    class Meta:
        db_table = "incomes"
        ordering = ["-date", "-time"]

    def __str__(self):
        return f"{self.title} - {self.total} ({self.date})"