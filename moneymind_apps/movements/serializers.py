from rest_framework import serializers
from .models import Expense
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
        ]
        read_only_fields = ["id", "user"]

    def create(self, validated_data):
        print(">>> Entrando a ExpenseSerializer.create", flush=True)
        print(f">>> validated_data inicial: {validated_data}", flush=True)

        user_id = validated_data.pop("user_id")
        print(f">>> user_id recibido: {user_id}", flush=True)

        user = User.objects.get(id=user_id)  # ← Ahora funcionará correctamente
        print(f">>> Usuario encontrado: {user}", flush=True)

        validated_data["user"] = user
        print(f">>> validated_data final: {validated_data}", flush=True)

        expense = super().create(validated_data)
        print(f">>> Expense creado correctamente: {expense}", flush=True)

        return expense