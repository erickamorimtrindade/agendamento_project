from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
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
    
class IdentificarUsuarioForm(forms.Form):
    """
    Etapa 1: identifica o usuário pelo nome cadastrado.
    """
    nome = forms.CharField(
        label="Nome do usuário",
        max_length= 100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Digite seu nome",
            "autofocus": True,
        })
    )
    telefone = forms.CharField(
        label="Telefone cadastrado",
        max_length=15,
        widget=forms.TextInput(attrs={"placeholder": "Ex: (83) 90000-0000"})
    )
class RedefinirSenhaForm(forms.Form):
    """
    Etapa 2: recebe e valida a nova senha do usuário já identificado.
    """
    nova_senha = forms.CharField(
        label="Nova senha",
        min_length=5,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Mínimo 5 caracteres",
        })
    )
    confirmar_senha = forms.CharField(
        label="Confirmar nova senha",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Repita a nova senha",
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        nova = cleaned_data.get("nova_senha")
        confirmar = cleaned_data.get("confirmar_senha")

        # Validação: campos vazios já são capturados pelo min_length,
        # mas verificamos a igualdade só se ambos estiverem presentes.
        if nova and confirmar and nova != confirmar:
            # erro amigável associado ao campo correto
            self.add_error(
                "confirmar_senha",
                "As senhas não coincidem. Digite novamente."
            )

        return cleaned_data
    
class AgendamentoManualForm(forms.Form):
    """
    Formulário para criação de agendamentos manuais pelo administrador.
    Não cria conta de usuário nem exige cadastro de cliente.
    """
    nome = forms.CharField(
        label='Nome da cliente',
        max_length=40,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nome completo',
            'autofocus': True,
        }),
    )
    telefone = forms.CharField(
        label='Telefone',
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '(83) 90000-0000',
        }),
    )
    servico = forms.ModelChoiceField(
        label='Serviço',
        queryset=None,
        empty_label='— Selecione um serviço —',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    data = forms.DateField(
        label='Data',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': date.today().isoformat(),
        }),
    )
    horario = forms.TimeField(
        label='Horário',
        widget=forms.Select(attrs={'class': 'form-select'}),
        input_formats=['%H:%M'],
    )
    descricao = forms.CharField(
        label='Observações (opcional)',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Anotações sobre o atendimento…',
        }),
    )

    def __init__(self, *args, horarios_disponiveis=None, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Servico as ServicoModel
        self.fields['servico'].queryset = ServicoModel.objects.filter(ativo=True)

        choices = [('', '— Selecione a data primeiro —')]
        if horarios_disponiveis:
            choices = [(h, h) for h in horarios_disponiveis]
        self.fields['horario'].widget.choices = choices