from rest_framework import serializers
from .models import *

class RecurringPaymentSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = RecurringPaymentReminder
        fields = [
            'id',
            'user_id',
            'name',
            'category',
            'amount',
            'recurrence_type',
            'payment_day',
            'is_active',
            'start_date',
            'end_date',
            'last_payment_date',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'last_payment_date']

    def create(self, validated_data):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user_id = validated_data.pop('user_id')
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError({"user_id": "Usuario no encontrado."})

        validated_data['user'] = user
        return super().create(validated_data)