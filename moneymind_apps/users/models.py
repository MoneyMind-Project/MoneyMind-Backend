from django.contrib.auth.models import AbstractUser
from django.db import models
from enum import Enum

class UserPlan(Enum):
    STANDARD = "standard"
    PREMIUM = "premium"

class Gender(Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class User(AbstractUser):

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[(tag.value, tag.value) for tag in Gender],
        null=True,
        blank=True
    )

    plan = models.CharField(
        max_length=20,
        choices=[(tag.value, tag.value) for tag in UserPlan],
        default=UserPlan.STANDARD.value,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = "users"

    def __str__(self):
        return f"{self.email} ({self.plan})"
