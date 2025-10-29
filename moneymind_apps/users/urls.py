from django.urls import path
from .views import *

urlpatterns = [
    path('register/', RegisterView.as_view(), name='user-register'),
    path('login/', LoginView.as_view(), name='user-login'),
    path('logout/', LogoutView.as_view(), name='user-logout'),
    path('list/', UserListView.as_view(), name='user-list'),  # solo GET todos los usuarios
    path('update-profile/', UpdateUserProfileView.as_view(), name='update-profile'),
    path('user-preferences/<int:user_id>/',UserPreferenceUpsertView.as_view(),name='user_preference_upsert'
    ),

]
