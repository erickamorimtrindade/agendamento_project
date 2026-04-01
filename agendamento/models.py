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

    def __str__(self):
        return self.id_usuario.username


class Agendamento(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    servico = models.ForeignKey('Servico', on_delete=models.CASCADE, null=True, blank=True)
    data = models.DateField()
    horario = models.TimeField()
    descricao = models.CharField(max_length=100, blank=True)

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

        # Data passada
        if self.data and self.data < now.date():
            errors['data'] = 'Não é permitido agendar em datas passadas.'

        # Horário inválido (fora do expediente)
        if self.horario:
            if self.horario < time(8,0) or self.horario > time(22,0):
                errors['horario'] = 'Horário permitido apenas entre 08:00 e 22:00.'

        # Horário inválido (mesmo dia)
        if self.data == now.date() and self.horario:
            if self.horario <= now.time():
                errors['horario'] = 'Não é possível agendar horários anteriores ao horário atual.'
        
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.cliente.id_usuario.username} - {self.data} {self.horario}"

#Mostra servicos disponiveis
class Servico(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.CharField(max_length=200, blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome