from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from .models import User
from .serializers import *
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from moneymind_apps.balances.models import Balance
from moneymind_apps.balances.views import *
from django.db import IntegrityError

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

# Registro simple
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Crear el usuario
                user = User.objects.create_user(
                    username=serializer.validated_data['email'],
                    email=serializer.validated_data['email'],
                    password=request.data.get('password'),
                    first_name=serializer.validated_data['first_name'],
                    last_name=serializer.validated_data['last_name'],
                    birth_date=serializer.validated_data.get('birth_date'),
                    gender=serializer.validated_data.get('gender'),
                    plan=serializer.validated_data.get('plan', 'standard')
                )

                # Crear el balance automáticamente
                Balance.objects.create(
                    user=user,
                    current_amount=request.data.get('current_amount'),   # requerido
                    monthly_income=request.data.get('monthly_income', None)  # opcional
                )

                return Response({
                    "message": "Registro exitoso"
                }, status=status.HTTP_201_CREATED)

            except IntegrityError:
                return Response({
                    "message": "El correo ya está en uso. Por favor intenta con otro."
                }, status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:
                return Response({
                    "message": f"Ocurrió un error inesperado: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "message": "Datos inválidos",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

# Login simple (solo validación de credenciales)
class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(request, email=email, password=password)
        if user is not None:
            # Crear o recuperar token
            token, created = Token.objects.get_or_create(user=user)

            serializer = UserSerializer(user)
            return Response({
                "message": "Login exitoso",
                "token": token.key,  # <- aquí va el token
                "user": serializer.data
            })
        else:
            return Response({"message": "Email o contraseña incorrectos"}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]  # solo usuarios autenticados pueden cerrar sesión

    def post(self, request):
        user = request.user
        # eliminamos el token del usuario
        Token.objects.filter(user=user).delete()
        return Response({"message": "Logout exitoso"}, status=status.HTTP_200_OK)

class UserListView(APIView):
    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

class UpdateUserProfileView(APIView):
    permission_classes = [AllowAny]

    def patch(self, request):
        user_id = request.data.get("user_id")
        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")
        gender = request.data.get("gender")
        birth_date = request.data.get("birth_date")
        monthly_income = request.data.get("monthly_income")

        # Validar user_id
        if not user_id:
            return Response(
                {"error": "user_id es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Buscar usuario
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "Usuario no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Actualizar campos del usuario si vienen en el request
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if gender is not None:
            user.gender = gender
        if birth_date is not None:
            user.birth_date = birth_date

        user.save()

        # Actualizar el monthly_income en Balance si viene en el request
        if monthly_income is not None:
            try:
                # Buscar o crear el Balance del usuario
                balance, created = Balance.objects.get_or_create(
                    user=user,
                    defaults={
                        'current_amount': 0,
                        'monthly_income': monthly_income
                    }
                )

                # Si ya existía, solo actualizar monthly_income
                if not created:
                    balance.monthly_income = monthly_income
                    balance.save()

            except Exception as e:
                return Response(
                    {"error": f"Error al actualizar ingreso mensual: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Obtener el balance actualizado para devolverlo
        try:
            balance = Balance.objects.get(user=user)
            monthly_income_value = balance.monthly_income
        except Balance.DoesNotExist:
            monthly_income_value = None

        return Response({
            "success": True,
            "message": "Perfil actualizado correctamente",
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "gender": user.gender,
                "birth_date": user.birth_date,
                "plan": user.plan
            },
            "monthly_income": float(monthly_income_value) if monthly_income_value else None
        }, status=status.HTTP_200_OK)


class UserPreferenceUpsertView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        """Obtiene la preferencia de color por user_id"""
        try:
            user_pref = UserPreference.objects.get(user_id=user_id)
        except UserPreference.DoesNotExist:
            return Response({"error": "Preferencia no encontrada"}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserPreferenceSerializer(user_pref)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, user_id):
        """Crea o actualiza la preferencia de color de un usuario"""
        data = request.data.copy()
        data['user'] = user_id  # Aseguramos que el serializer tenga el user_id

        try:
            user_pref = UserPreference.objects.get(user_id=user_id)
            # Si existe, actualizamos
            serializer = UserPreferenceSerializer(user_pref, data=data, partial=True)
            action = "actualizada"
        except UserPreference.DoesNotExist:
            # Si no existe, creamos
            serializer = UserPreferenceSerializer(data=data)
            action = "creada"

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": f"Preferencia {action} exitosamente", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

