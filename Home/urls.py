from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('registro/', views.registro, name='registro'),
    path('panel/', views.panel, name='panel'),
    path('login/', views.index, name='login'),  # Para el action del form
    path('logout/', views.logout_view, name='logout'),
    
    # NUEVAS APIs para Android
    path('api/medicamentos/', views.api_medicamentos, name='api_medicamentos'),
    path('api/login/', views.api_login, name='api_login'),
    path('api/logout/', views.api_logout, name='api_logout'),
    path('api/mi-id/', views.api_mi_id, name='api_mi_id'),  # ← ESTA FALTA
]