from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),  
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('agendar/', views.criar_agendamento, name='agendar'),
    path('agendamento/', views.listar_agendamentos, name='listar_agendamentos'),
    path('agendamento/excluir/<int:id>', views.excluir_agendamento, name='excluir_agendamento'),
]