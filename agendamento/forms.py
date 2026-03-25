from django import forms
from .models import Agendamento

class AgendamentoForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = ['data', 'horario', 'descricao']

        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
            'horario': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        data = cleaned_data.get('data')
        horario = cleaned_data.get('horario')

        if not data or not horario:
            return cleaned_data
        
        if Agendamento.objects.filter(data=data, horario=horario).exists():
            raise forms.ValidationError("Este horário já está ocupado.")
        
        return cleaned_data