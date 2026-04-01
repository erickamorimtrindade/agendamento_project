from django.contrib import admin
from .models import Cliente, Agendamento, Servico

class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'data', 'horario')

admin.site.register(Cliente)
admin.site.register(Agendamento, AgendamentoAdmin)
admin.site.register(Servico)

# Register your models here.
