from django.contrib import admin
from .models import Cliente, Agendamento

class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'data', 'horario')

admin.site.register(Cliente)  # 👈 ISSO FALTAVA
admin.site.register(Agendamento, AgendamentoAdmin)

# Register your models here.
