from django import forms
from .models import Agendamento
from datetime import date, time

class AgendamentoForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = ['data', 'horario', 'descricao']

        widgets = {
            'data': forms.DateInput(attrs={
                'type': 'date',
                'min': date.today().isoformat(),
                'onkeydown': 'return false;',
                'onclick': 'this.showPicker()',
                'onfocus': 'this.showPicker()',
            }),
            'horario': forms.HiddenInput()  
        }

    def clean(self):
        cleaned_data = super().clean()
        data = cleaned_data.get('data')
        horario = cleaned_data.get('horario')

        if data and data < date.today():
            raise forms.ValidationError("Não é possível agendar em datas passadas.")

        
        if horario:
            if horario < time(8, 0) or horario > time(22, 0):
                raise forms.ValidationError("Horário permitido apenas entre 08:00 e 22:00.")

        
        if data and horario and Agendamento.objects.filter(data=data, horario=horario).exists():
            raise forms.ValidationError("Este horário já está ocupado.")
        
        return cleaned_data