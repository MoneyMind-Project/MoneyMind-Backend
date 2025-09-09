from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import User

class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        error_messages={
            "unique": _("Ya existe un usuario con este correo electrónico.")
        }
    )

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'birth_date', 'gender', 'plan']
        read_only_fields = ['id']
