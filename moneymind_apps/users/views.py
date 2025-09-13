from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from .models import User
from .serializers import UserSerializer
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from moneymind_apps.balances.models import Balance
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