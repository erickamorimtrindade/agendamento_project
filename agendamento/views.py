from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Cliente, Agendamento


def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            return render(request, 'agendamento/register.html', {'erro': 'As senhas não coincidem!'})

        if User.objects.filter(username=username).exists():
            return render(request, 'agendamento/register.html', {'erro': 'Já existe um usuário com este nome!'})

        user = User.objects.create_user(username=username, password=password)
        Cliente.objects.create(usuario=user)

        return redirect('login')

    return render(request, 'agendamento/register.html')


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


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def home(request):
    return render(request, 'agendamento/home.html')


@login_required
def criar_agendamento(request):
    if request.method == "POST":
        data = request.POST.get("data")
        horario = request.POST.get("horario")
        descricao = request.POST.get("descricao")

        cliente = Cliente.objects.get(usuario=request.user)

        if Agendamento.objects.filter(data=data, horario=horario).exists():
            return render(request, 'agendamento/agendar.html', {'erro': 'Horário já ocupado!'})

        Agendamento.objects.create(
            cliente=cliente,
            data=data,
            horario=horario,
            descricao=descricao
        )

        return redirect('listar_agendamentos')

    return render(request, 'agendamento/agendar.html')


@login_required
def listar_agendamentos(request):
    cliente = Cliente.objects.get(usuario=request.user)
    agendamentos = Agendamento.objects.filter(cliente=cliente)

    return render(request, 'agendamento/lista.html', {'agendamentos': agendamentos})

# Create your views here.
