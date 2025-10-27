from rest_framework import serializers
from .models import Expense, Income
from django.contrib.auth import get_user_model  # ← CAMBIAR ESTA LÍNEA

User = get_user_model()  # ← AGREGAR ESTA LÍNEA

class ExpenseSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Expense
        fields = [
            "id",
            "user",
            "user_id",
            "category",
            "place",
            "date",
            "time",
            "total",
            "comment",
            "created_at",
        ]
        read_only_fields = ["id", "user", "created_at"]

    def create(self, validated_data):
        user_id = validated_data.pop("user_id")
        user = User.objects.get(id=user_id)  # ← Ahora funcionará correctamente
        validated_data["user"] = user
        expense = super().create(validated_data)
        return expense

class IncomeSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Income
        fields = [
            "id",
            "user",
            "user_id",
            "title",
            "date",
            "time",
            "total",
            "comment",
            'is_recurring',
            "created_at",
        ]
        read_only_fields = ["id", "user", "created_at"]

    def create(self, validated_data):
        user_id = validated_data.pop("user_id")
        user = User.objects.get(id=user_id)
        validated_data["user"] = user
        income = super().create(validated_data)
        return income