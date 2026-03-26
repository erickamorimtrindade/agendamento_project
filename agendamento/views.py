from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Cliente, Agendamento
from .forms import AgendamentoForm
from datetime import datetime, timedelta
from django.db import IntegrityError
from django.core.exceptions import ValidationError

def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            return render(request, 'agendamento/register.html', {'erro': 'As senhas não coincidem!'})

        if User.objects.filter(username=username).exists():
            return render(request, 'agendamento/register.html', {'erro': 'Usuário já existe!'})

        user = User.objects.create_user(username=username, password=password)
        # cria cliente automaticamente
        Cliente.objects.get_or_create(id_usuario=user)

        return redirect('login')

    return render(request, 'agendamento/register.html')

#Login
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect('home')

        return render(request, 'agendamento/login.html', {'erro': 'Login inválido'})

    return render(request, 'agendamento/login.html')

#Logout
def logout_view(request):
    logout(request)
    return redirect('login')

#Home
@login_required
def home(request):
    return render(request, 'agendamento/home.html')

# GERAR HORÁRIOS (08:00 até 22:00 de 30 em 30 min)
def gerar_horarios():
    horarios = []
    inicio = datetime.strptime("08:00", "%H:%M")
    fim = datetime.strptime("22:00", "%H:%M")

    while inicio <= fim:
        horarios.append(inicio.strftime("%H:%M"))
        inicio += timedelta(minutes=30)

    return horarios

#Criar agendamentos
@login_required
def criar_agendamento(request):
    cliente, _ = Cliente.objects.get_or_create(id_usuario=request.user)
    horarios = gerar_horarios()


    if request.method == "POST":
        form = AgendamentoForm(request.POST)

        if form.is_valid():
            agendamento = form.save(commit=False)
            agendamento.cliente = cliente
            try:
                agendamento.full_clean() # chama o clean() do model
                agendamento.save()
                return redirect ('listar_agendamentos')
            except ValidationError as e:
                for field, errors in e.message_dict.items():
                    for error in errors:
                        form.add_error(field, error)

            except IntegrityError:
                form.add_error(None, "Esse horário acabou de ser ocupado. Tente outro.")

    else:
        form = AgendamentoForm()

    return render(request, 'agendamento/agendar.html', {
        'form': form,
        'horarios': horarios
    })

#Listar agendamentos
@login_required
def listar_agendamentos(request):
    cliente, _ = Cliente.objects.get_or_create(id_usuario=request.user)
    agendamentos = Agendamento.objects.filter(cliente=cliente)

    return render(request, 'agendamento/lista.html', {
        'agendamentos': agendamentos
    })