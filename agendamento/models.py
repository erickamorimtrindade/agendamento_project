from django.db import models
from django.contrib.auth.models import User


class Cliente(models.Model):
    id_usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True
    )
    telefone = models.CharField(max_length=20,)
    endereco = models.CharField(max_length=200,)

    def __str__(self):
        return self.id_usuario.username


class Agendamento(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    data = models.DateField()
    horario = models.TimeField()
    descricao = models.CharField(max_length=60, blank=True)

    

    def __str__(self):
        return f"{self.cliente.id_usuario.username} - {self.data} {self.horario}"


# Create your models here.
