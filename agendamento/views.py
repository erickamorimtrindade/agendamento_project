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
            return render(request, 'register.html', {'erro': 'As senhas não coincidem!'})

        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'erro': 'Já existe um usuário com este nome!'})

        user = User.objects.create_user(username=username, password=password)
        Cliente.objects.create(id_usuario=user)

        return redirect('login')

    return render(request, 'register.html')

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect('home')

        return render(request, 'login.html', {'erro': 'Login inválido'})

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def home(request):
    return render(request, 'home.html')

@login_required
def criar_agendamento(request):
    cliente = Cliente.objects.get(id_usuario=request.user)

    if request.method == "POST":
        form = AgendamentoForm(request.POST)
        
        if form.is_valid():
            agendamento = form.save(commit=False)
            agendamento.cliente = cliente
            agendamento.save()

            return redirect('listar_agendamentos')
        return render(request, 'agendar.html', {'form': form})

    form = AgendamentoForm()
    return render(request, 'agendar.html', {'form': form})

@login_required
def listar_agendamentos(request):
    cliente = Cliente.objects.get(id_usuario=request.user)
    agendamentos = Agendamento.objects.filter(cliente=cliente)

    return render(request, 'lista.html', {'agendamentos': agendamentos})

# Create your views here.
