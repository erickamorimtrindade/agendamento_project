from django import forms
from .models import Agendamento
from datetime import date, time, datetime

class AgendamentoForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = ['data', 'horario', 'descricao']
        widgets = {
            'data': forms.DateInput(attrs={
                'type': 'text',
                'onchange': 'this.form.submit()',
                'class': 'form-control',
                'id': 'data',
                'min': date.today().isoformat(),
            }),
            'horario': forms.HiddenInput(),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Digite uma descrição para o agendamento',
                'rows': 4,
            }),
        }
        labels = {
            'data': 'Data',
            'descricao': 'Descrição',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['horario'].required = False

    def clean_data(self):
        data = self.cleaned_data.get('data')
        if not data:
            raise forms.ValidationError("Selecione uma data.")
        return data

    def clean_horario(self):
        horario = self.cleaned_data.get('horario')

        if not horario:
            raise forms.ValidationError('Selecione um horário antes de agendar.')

        return horario

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