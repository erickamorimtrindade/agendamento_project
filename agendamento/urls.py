from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),  
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('servicos/', views.escolher_servico, name='escolher_servico'),
    path('agendar/', views.criar_agendamento, name='agendar'),
    path('agendamento/', views.listar_agendamentos, name='listar_agendamentos'),
    path('agendamento/excluir/<int:id>', views.excluir_agendamento, name='confirmar_exclusao'),
    path('painel/', views.painel_admin, name='painel_admin'),
    path('painel/servicos/', views.listar_servicos, name='listar_servicos'),
    path('painel/servicos/criar/', views.criar_servico, name='criar_servico'),
    path('painel/servicos/editar/<int:id>/', views.editar_servico, name='editar_servico'),
    path('painel/servicos/excluir/<int:id>/', views.excluir_servico, name='excluir_servico'),
    path('painel/relatorio/hoje/', views.agendamentos_hoje, name='agendamentos_hoje'),
    path('painel/relatorio/31dias/', views.relatorio_31_dias, name='relatorio_31_dias'),
]