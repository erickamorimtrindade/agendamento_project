from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Cliente, Agendamento, Servico
from .forms import AgendamentoForm
from datetime import datetime, timedelta, date
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.admin.views.decorators import staff_member_required
from collections import defaultdict
import json


#painel do dono --------

@staff_member_required
def criar_servico(request):
    if request.method == "POST":
        nome = request.POST.get("nome")
        descricao = request.POST.get("descricao")
        preco = request.POST.get("preco")

        Servico.objects.create(
            nome=nome,
            descricao=descricao,
            preco=preco
        )

        return redirect("listar_servicos")

    return render(request, "admin/criar_servico.html")


@staff_member_required
def listar_servicos(request):
    servicos = Servico.objects.all()
    return render(request, "admin/listar_servicos.html", {"servicos": servicos})


@staff_member_required
def editar_servico(request, id):
    servico = get_object_or_404(Servico, id=id)

    if request.method == "POST":
        servico.nome = request.POST.get("nome")
        servico.descricao = request.POST.get("descricao")
        servico.preco = request.POST.get("preco")
        servico.save()

        return redirect("listar_servicos")

    return render(request, "admin/editar_servico.html", {"servico": servico})


@staff_member_required
def excluir_servico(request, id):
    servico = get_object_or_404(Servico, id=id)

    if request.method == "POST":
        servico.delete()
        return redirect("listar_servicos")

    return render(request, "admin/confirmar_exclusao_servico.html", {"servico": servico})

@staff_member_required
def agendamentos_hoje(request):
    hoje = date.today()
    agendamentos = Agendamento.objects.filter(data=hoje)

    return render(request, "admin/relatorio_hoje.html", {
        "agendamentos": agendamentos
    })

@staff_member_required
def relatorio_31_dias(request):
    hoje = date.today()
    inicio = hoje - timedelta(days=31)

    agendamentos = Agendamento.objects.filter(
        data__range=[inicio, hoje],
        status='presente'
    ).order_by('data')

    # 💰 TOTAL
    total = sum(float(ag.servico.preco) for ag in agendamentos)

    # 📈 FATURAMENTO POR DIA
    faturamento_por_dia = defaultdict(float)

    for ag in agendamentos:
        faturamento_por_dia[str(ag.data)] += float(ag.servico.preco)

    datas_ordenadas = sorted(faturamento_por_dia.keys())
    valores_ordenados = [faturamento_por_dia[d] for d in datas_ordenadas]

    # 🍩 SERVIÇOS
    servicos = Servico.objects.all()
    servicos_dict = {s.nome: 0 for s in servicos}

    for ag in agendamentos:
        servicos_dict[ag.servico.nome] += float(ag.servico.preco)

    # remove serviços zerados (corrige bug do gráfico)
    servicos_dict = {k: v for k, v in servicos_dict.items() if v > 0}

    servicos_labels = list(servicos_dict.keys())
    servicos_valores = list(servicos_dict.values())

    # 📊 DIAS DA SEMANA
    dias_semana = {
        "Monday": 0,
        "Tuesday": 0,
        "Wednesday": 0,
        "Thursday": 0,
        "Friday": 0,
        "Saturday": 0,
        "Sunday": 0,
    }

    for ag in agendamentos:
        dia = ag.data.strftime("%A")
        dias_semana[dia] += 1

    traducao = {
        "Monday": "Seg",
        "Tuesday": "Ter",
        "Wednesday": "Qua",
        "Thursday": "Qui",
        "Friday": "Sex",
        "Saturday": "Sáb",
        "Sunday": "Dom",
    }

    dias_labels = []
    dias_valores = []

    for dia, valor in dias_semana.items():
        dias_labels.append(traducao[dia])
        dias_valores.append(valor)

    # 🏆 SERVIÇO TOP
    servico_top = max(servicos_dict, key=servicos_dict.get) if servicos_dict else "Nenhum"

    # TOTAL DE AGENDAMENTOS (inclui presentes + ausentes)
    total_agendamentos = Agendamento.objects.filter(
    data__range=[inicio, hoje]
    ).count()

# AUSENTES
    total_ausentes = Agendamento.objects.filter(
    data__range=[inicio, hoje],
    status='ausente'
    ).count()

# TAXA DE AUSÊNCIA (%)
    taxa_ausencia = 0
    if total_agendamentos > 0:
        taxa_ausencia = (total_ausentes / total_agendamentos) * 100

    return render(request, "admin/relatorio_31.html", {
        "agendamentos": agendamentos,
        "total": total,
        "datas": json.dumps(datas_ordenadas),
        "valores": json.dumps(valores_ordenados),
        "servicos_labels": json.dumps(servicos_labels),
        "servicos_valores": json.dumps(servicos_valores),
        "dias_labels": json.dumps(dias_labels),
        "dias_valores": json.dumps(dias_valores),
        "servico_top": servico_top,
        "total_agendamentos": total_agendamentos,
        "taxa_ausencia": round(taxa_ausencia, 1)
    })


@staff_member_required
def painel_admin(request):
    return render(request, 'admin/painel_admin.html')

@staff_member_required
def atualizar_status(request, id, status):
    ag = get_object_or_404(Agendamento, id=id)

    ag.status = status
    ag.save()

    return redirect('agendamentos_hoje')

#--------------------------------------------------------------------------------------------------------

#painel do usuario

def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        telefone = request.POST.get("telefone")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            return render(request, 'clients/register.html', {'erro': 'As senhas não coincidem!'})

        if User.objects.filter(username=username).exists():
            return render(request, 'clients/register.html', {'erro': 'Usuário já existe!'})

        user = User.objects.create_user(username=username, password=password)
        # cria cliente automaticamente
        cliente, _ = Cliente.objects.get_or_create(id_usuario=user)
        cliente.telefone = telefone
        cliente.save()

        return redirect('login')

    return render(request, 'clients/register.html')

#Login
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)

            if user.is_staff:
                return redirect('painel_admin')  
            else:
                return redirect('home')

        return render(request, 'clients/login.html', {'erro': 'Login inválido'})

    return render(request, 'clients/login.html')

#Logout
def logout_view(request):
    logout(request)
    return redirect('login')

#Home
@login_required
def home(request):
    return render(request, 'clients/home.html')

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

    # NOVO: pega o serviço escolhido antes
    servico_id = request.session.get("servico_id")

    # NOVO: se o usuário não escolheu serviço, volta pra página de serviços
    if not servico_id:
        return redirect("escolher_servico")

    # NOVO: busca o serviço no banco
    servico = get_object_or_404(Servico, id=servico_id, ativo=True)

    horarios = gerar_horarios()
    horarios_ocupados = []

    data_selecionada = request.GET.get("data") or request.POST.get("data")
    data_convertida = None

    if data_selecionada:
        try:
            data_convertida = datetime.strptime(data_selecionada, "%d/%m/%Y").date()
        except ValueError:
            try:
                data_convertida = datetime.strptime(data_selecionada, "%Y-%m-%d").date()
            except ValueError:
                data_convertida = None

    if data_convertida:
        agendamentos_do_dia = Agendamento.objects.filter(data=data_convertida)
        horarios_ocupados = [
            ag.horario.strftime("%H:%M") for ag in agendamentos_do_dia
        ]

    if request.method == "POST":
        form = AgendamentoForm(request.POST)
        horario_selecionado = request.POST.get("horario")

        ja_existe = False
        if data_convertida and horario_selecionado:
            ja_existe = Agendamento.objects.filter(
                data=data_convertida,
                horario=horario_selecionado
            ).exists()

        if ja_existe:
            form.add_error("horario", "Esse horário já está ocupado para essa data.")
        elif form.is_valid():
            agendamento = form.save(commit=False)
            agendamento.cliente = cliente
            # NOVO: salva o serviço no agendamento
            agendamento.servico = servico

            try:
                agendamento.full_clean()
                agendamento.save()

                # OPCIONAL: limpa a sessão depois de agendar
                request.session.pop("servico_id", None)

                return redirect('listar_agendamentos')

            except ValidationError as e:
                for field, errors in e.message_dict.items():
                    for error in errors:
                        form.add_error(field, error)

            except IntegrityError:
                form.add_error("horario", "Esse horário acabou de ser ocupado. Tente outro.")
    else:
        form = AgendamentoForm(initial={"data": data_selecionada})

    return render(request, 'clients/agendar.html', {
        'form': form,
        'horarios': horarios,
        'horarios_ocupados': horarios_ocupados,
        'data_selecionada': data_selecionada,
        'servico': servico,  # NOVO: manda o serviço pra tela
    })

#Listar agendamentos
@login_required
def listar_agendamentos(request):
    limpar_agendamentos_vencidos()

    cliente, _ = Cliente.objects.get_or_create(id_usuario=request.user)

    agendamentos = Agendamento.objects.filter(cliente=cliente).order_by('data', 'horario')

    return render(request, 'clients/lista.html', {
        'agendamentos': agendamentos
    })

@login_required
def excluir_agendamento(request, id):
    cliente, _ = Cliente.objects.get_or_create(id_usuario=request.user)

    # Impede usuário deletar agendamento de outro
    agendamento = get_object_or_404(Agendamento, id=id, cliente=cliente)

    if request.method == 'POST':
        agendamento.delete()
        return redirect('listar_agendamentos')
    
    return render (request, 'clients/confirmar_exclusao.html', {
        'agendamento': agendamento
    })

#Limpa os agendamentos que ja passaram o horario quando o cliente abre o site
def limpar_agendamentos_vencidos():
    hoje = date.today()
    agora = datetime.now().time()

    Agendamento.objects.filter(data__lt=hoje).delete()
    Agendamento.objects.filter(data=hoje, horario__lt=agora).delete()

@login_required
def escolher_servico(request):
    servicos = Servico.objects.filter(ativo=True)
    erro = None
    
    if request.method == "POST":
        servico_id = request.POST.get("servico")

        if not servico_id:
            erro = "Selecione um serviço para continuar."
        else:
            request.session["servico_id"] = servico_id
            return redirect("agendar")

    return render(request, "clients/servicos.html", {
        "servicos": servicos,
        "erro": erro,
    })