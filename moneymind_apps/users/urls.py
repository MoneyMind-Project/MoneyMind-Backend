from django.urls import path
from .views import RegisterView, LoginView, UserListView, LogoutView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='user-register'),
    path('login/', LoginView.as_view(), name='user-login'),
    path('logout/', LogoutView.as_view(), name='user-logout'),
    path('list/', UserListView.as_view(), name='user-list'),  # solo GET todos los usuarios
]
