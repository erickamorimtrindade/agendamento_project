from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Cliente, Agendamento
from .forms import AgendamentoForm


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
        Cliente.objects.create(id_usuario=user)

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
    cliente, created = Cliente.objects.get_or_create(id_usuario=request.user)


    if request.method == "POST":
        form = AgendamentoForm(request.POST)

        if form.is_valid():
            agendamento = form.save(commit=False)
            agendamento.cliente = cliente
            agendamento.save()
            return redirect('listar_agendamentos')

    else:
        form = AgendamentoForm()

    return render(request, 'agendamento/agendar.html', {'form': form})


@login_required
def listar_agendamentos(request):
    cliente, created = Cliente.objects.get_or_create(id_usuario=request.user)
    agendamentos = Agendamento.objects.filter(cliente=cliente)

    return render(request, 'agendamento/lista.html', {'agendamentos': agendamentos})