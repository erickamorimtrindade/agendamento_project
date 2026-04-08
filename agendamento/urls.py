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
    path('painel/agendamento/status/<int:id>/<str:status>/', views.atualizar_status, name='atualizar_status'),
    path('painel/proximos-agendamentos/', views.proximos_agendamentos, name='proximos_agendamentos'),
    path('gerenciar-horarios/', views.gerenciar_horarios, name='gerenciar_horarios'),
    path('bloquear-horario/', views.bloquear_horario, name='bloquear_horario'),
    path('desbloquear-horario/', views.desbloquear_horario, name='desbloquear_horario'),
    path('bloquear-dia/', views.bloquear_dia, name='bloquear_dia'),
    path('desbloquear-dia/', views.desbloquear_dia, name='desbloquear_dia'),
    path('liberar-horario/', views.liberar_horario, name='liberar_horario'),

]