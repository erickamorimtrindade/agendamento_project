from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import time

class Cliente(models.Model):
    id_usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True
    )
    telefone = models.CharField(max_length=20,)
    endereco = models.CharField(max_length=60,)
    bloqueado = models.BooleanField(default=False)

    def __str__(self):
        return self.id_usuario.username


class Agendamento(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    servico = models.ForeignKey('Servico', on_delete=models.CASCADE, null=True, blank=True)
    data = models.DateField()
    horario = models.TimeField()
    descricao = models.CharField(max_length=100, blank=True)
    status = models.CharField(
    max_length=10,
    choices=[
        ('pendente', 'Pendente'),
        ('presente', 'Presente'),
        ('ausente', 'Ausente')
    ],
    default='pendente'
)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields= ['data', 'horario'],
                name = 'unique_agendamento_data_horario'
            )
        ]

    def clean(self):
        errors = {}

        now = timezone.localtime()

        if self.data and self.data < now.date():
            errors['data'] = 'Não é permitido agendar em datas passadas.'

        if self.horario:
            if self.horario < time(8, 0) or self.horario > time(22, 0):
                errors['horario'] = 'Horário permitido apenas entre 08:00 e 22:00.'

        if self.data == now.date() and self.horario:
            if self.horario <= now.time():
                errors['horario'] = 'Não é possível agendar horários anteriores ao horário atual.'

        # ── Regra de antecedência mínima de 24 horas ──────────────────────
        # Só executa se data e horário estão presentes e ainda não houve erro neles.
        if 'data' not in errors and 'horario' not in errors:
            if self.data and self.horario:
                from datetime import datetime as dt
                from zoneinfo import ZoneInfo

                tz = ZoneInfo('America/Sao_Paulo')

                # Monta o datetime do agendamento com timezone
                agendamento_naive = dt.combine(self.data, self.horario)
                agendamento_dt = agendamento_naive.replace(tzinfo=tz)

                # Momento atual com timezone
                agora = timezone.localtime()

                diferenca = agendamento_dt - agora

                if diferenca.total_seconds() < 86400:  # 86400 s = 24 horas exatas
                    errors['horario'] = (
                        'Agendamentos devem ser feitos com pelo menos 24 horas de antecedência. '
                        'Escolha uma data e horário a partir de '
                        f'{(agora + __import__("datetime").timedelta(hours=24)).strftime("%d/%m/%Y às %H:%M")}.'
                    )
        # ──────────────────────────────────────────────────────────────────

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.cliente.id_usuario.username} - {self.data} {self.horario}"


class Servico(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.CharField(max_length=200, blank=True)
    ativo = models.BooleanField(default=True)
    preco = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    duracao_minutos = models.PositiveIntegerField(default=60)
    horario_duplo = models.BooleanField(
        default=False,
        verbose_name="Ocupa dois horários consecutivos"
    )

    def __str__(self):
        return f"{self.nome} - {self.preco}"
    

class NotificacaoExclusao(models.Model):
    """
    Armazena o aviso de exclusão de agendamento pelo ADM.
    Exibido como pop-up uma única vez ao cliente na próxima vez que entrar.
    """
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='notificacoes_exclusao')
    servico_nome = models.CharField(max_length=100)
    data_agendamento = models.DateField()
    horario_agendamento = models.TimeField()
    criado_em = models.DateTimeField(auto_now_add=True)
    visualizado = models.BooleanField(default=False)

    def __str__(self):
        return f"Notif. exclusão p/ {self.cliente} — {self.data_agendamento} {self.horario_agendamento}"


class HorarioBloqueado(models.Model):
    data = models.DateField()
    horario = models.TimeField(null=True, blank=True)
    tipo = models.CharField(max_length=10, choices=[
        ('bloqueio', 'Bloqueio'),
        ('liberado', 'Liberado')
    ])

    class Meta:
        unique_together = ['data', 'horario']