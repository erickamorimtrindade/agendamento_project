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
from .models import HorarioBloqueado
from django.utils import timezone


#painel do dono --------

@staff_member_required
def criar_servico(request):
    if request.method == "POST":
        nome = request.POST.get("nome")
        descricao = request.POST.get("descricao")
        preco = request.POST.get("preco")
        duracao = request.POST.get("duracao_minutos")

        Servico.objects.create(
            nome=nome,
            descricao=descricao,
            preco=preco,
            duracao_minutos=duracao
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
        servico.duracao_minutos = request.POST.get("duracao_minutos")
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
    hoje = timezone.localdate()
    inicio = hoje - timedelta(days=30) 

    agendamentos = Agendamento.objects.filter(
        data__range=[inicio, hoje],
        status='presente'
    ).order_by('data')

    total = sum(float(ag.servico.preco) for ag in agendamentos)

    faturamento_por_dia = defaultdict(float)

    for ag in agendamentos:
        faturamento_por_dia[ag.data.isoformat()] += float(ag.servico.preco)

    
    datas_ordenadas = []
    valores_ordenados = []

    for i in range(0, 31):
        dia = inicio + timedelta(days=i)
        dia_str = dia.isoformat()

        datas_ordenadas.append(dia.strftime("%d/%m"))
        valores_ordenados.append(round(faturamento_por_dia.get(dia_str, 0), 2))

    
    servicos = Servico.objects.all()
    servicos_dict = {s.nome: 0 for s in servicos}

    for ag in agendamentos:
        servicos_dict[ag.servico.nome] += float(ag.servico.preco)

    servicos_dict = {k: v for k, v in servicos_dict.items() if v > 0}

    servicos_labels = list(servicos_dict.keys())
    servicos_valores = list(servicos_dict.values())

    
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

    
    servico_top = max(servicos_dict, key=servicos_dict.get) if servicos_dict else "Nenhum"

    
    total_agendamentos = Agendamento.objects.filter(
        data__range=[inicio, hoje]
    ).count()

    
    total_ausentes = Agendamento.objects.filter(
        data__range=[inicio, hoje],
        status='ausente'
    ).count()

    
    taxa_ausencia = 0
    if total_agendamentos > 0:
        taxa_ausencia = (total_ausentes / total_agendamentos) * 100

    return render(request, "admin/relatorio_31.html", {
    "agendamentos": agendamentos,

    "faturamento_total": total,

    "labels_faturamento": json.dumps(datas_ordenadas),
    "dados_faturamento": json.dumps(valores_ordenados),

    "labels_servicos": json.dumps(servicos_labels),
    "dados_servicos": json.dumps(servicos_valores),

    "labels_semana": json.dumps(dias_labels),
    "dados_semana": json.dumps(dias_valores),

    "servico_mais_lucrativo": servico_top,
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

@staff_member_required
def proximos_agendamentos(request):

    data = request.GET.get("data")

    data_convertida = None

    if data:
        try:
            data_convertida = datetime.strptime(data, "%d/%m/%Y").date()
        except:
            try:
                data_convertida = datetime.strptime(data, "%Y-%m-%d").date()
            except:
                data_convertida = None

    hoje = date.today()

    if data_convertida:
        agendamentos = Agendamento.objects.filter(
            data=data_convertida
        ).order_by('data', 'horario')
    else:
        agendamentos = Agendamento.objects.filter(
            data__gte=hoje
        ).order_by('data', 'horario')

    return render(request, 'admin/proximos_agendamentos.html', {
        'agendamentos': agendamentos,
        'data': data
    })

def gerar_horarios():
    horarios = []
    inicio = datetime.strptime("08:00", "%H:%M")
    fim = datetime.strptime("22:00", "%H:%M")

    while inicio <= fim:
        horarios.append(inicio.strftime("%H:%M"))
        inicio += timedelta(minutes=30)

    return horarios

def converter_data(data):
    if not data:
        return None

    formatos = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"]

    for formato in formatos:
        try:
            return datetime.strptime(data, formato).date()
        except ValueError:
            continue

    return None


@staff_member_required
def gerenciar_horarios(request):
    data = request.GET.get("data")
    data_formatada = converter_data(data)

    horarios = gerar_horarios()

    bloqueados = []
    horarios_liberados = []
    dia_bloqueado = False

    if data_formatada:
        bloqueios = HorarioBloqueado.objects.filter(data=data_formatada)

        bloqueados = [
            b.horario.strftime("%H:%M")
            for b in bloqueios
            if b.tipo == "bloqueio" and b.horario
        ]

        horarios_liberados = [
            b.horario.strftime("%H:%M")
            for b in bloqueios
            if b.tipo == "liberado" and b.horario
        ]

        dia_bloqueado = bloqueios.filter(
            horario__isnull=True,
            tipo="bloqueio"
        ).exists()

    return render(request, "admin/gerenciar_horarios.html", {
        "horarios": horarios,
        "data": data or "",
        "bloqueados": bloqueados,
        "horarios_liberados": horarios_liberados,
        "dia_bloqueado": dia_bloqueado
    })

#bloquear horario
@staff_member_required
def bloquear_horario(request):
    if request.method == "POST":
        data = request.POST.get("data")
        horario = request.POST.get("horario")

        data_formatada = converter_data(data)

        if data_formatada and horario and data_formatada >= date.today():
            horario_formatado = datetime.strptime(horario, "%H:%M").time()


            HorarioBloqueado.objects.filter(
                data=data_formatada,
                horario=horario_formatado,
                tipo="liberado"
            ).delete()

            HorarioBloqueado.objects.update_or_create(
                data=data_formatada,
                horario=horario_formatado,
                defaults={"tipo": "bloqueio"}
            )

        return redirect(f"/gerenciar-horarios/?data={data}")

    return redirect("/gerenciar-horarios/")


#desbloquear horario
@staff_member_required
def desbloquear_horario(request):
    if request.method == "POST":
        data = request.POST.get("data")
        horario = request.POST.get("horario")

        data_formatada = converter_data(data)

        if data_formatada and horario and data_formatada >= date.today():
            horario_formatado = datetime.strptime(horario, "%H:%M").time()

            HorarioBloqueado.objects.filter(
                data=data_formatada,
                horario=horario_formatado,
                tipo="bloqueio"
            ).delete()

        return redirect(f"/gerenciar-horarios/?data={data}")

    return redirect("/gerenciar-horarios/")


#liberar horario
@staff_member_required
def liberar_horario(request):
    if request.method == "POST":
        data = request.POST.get("data")
        horario = request.POST.get("horario")

        data_formatada = converter_data(data)

        if data_formatada and horario and data_formatada >= date.today():
            horario_formatado = datetime.strptime(horario, "%H:%M").time()

            HorarioBloqueado.objects.filter(
                data=data_formatada,
                horario=horario_formatado,
                tipo="bloqueio"
            ).delete()

            HorarioBloqueado.objects.update_or_create(
                data=data_formatada,
                horario=horario_formatado,
                defaults={"tipo": "liberado"}
            )

        return redirect(f"/gerenciar-horarios/?data={data}")

    return redirect("/gerenciar-horarios/")


#bloquear dia inteiro
@staff_member_required
def bloquear_dia(request):
    if request.method == "POST":
        data = request.POST.get("data")
        data_formatada = converter_data(data)

        if data_formatada and data_formatada >= date.today():
            HorarioBloqueado.objects.update_or_create(
                data=data_formatada,
                horario=None,
                defaults={"tipo": "bloqueio"}
            )

        return redirect(f"/gerenciar-horarios/?data={data}")

    return redirect("/gerenciar-horarios/")


#desbloquear dia inteiro
@staff_member_required
def desbloquear_dia(request):
    if request.method == "POST":
        data = request.POST.get("data")
        data_formatada = converter_data(data)

        if data_formatada:

            HorarioBloqueado.objects.filter(
                data=data_formatada,
                horario=None,
                tipo="bloqueio"
            ).delete()

        return redirect(f"/gerenciar-horarios/?data={data}")

    return redirect("/gerenciar-horarios/")

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
    if request.user.is_staff:
        return redirect('painel_admin')  # admin vai pro painel

    return render(request, 'clients/home.html')  # cliente normal

#gerar horarios
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

    if request.user.is_staff:
        return redirect('painel_admin')

    cliente, _ = Cliente.objects.get_or_create(id_usuario=request.user)

    servico_id = request.session.get("servico_id")

    if not servico_id:
        return redirect("escolher_servico")

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


        bloqueado = False

        if data_convertida and horario_selecionado:
            horario_time = datetime.strptime(horario_selecionado, "%H:%M").time()

            bloqueios = HorarioBloqueado.objects.filter(data=data_convertida)

            dia_bloqueado = bloqueios.filter(
                horario__isnull=True,
                tipo='bloqueio'
            ).exists()

            horario_bloqueado = bloqueios.filter(
                horario=horario_time,
                tipo='bloqueio'
            ).exists()

            horario_liberado = bloqueios.filter(
                horario=horario_time,
                tipo='liberado'
            ).exists()

            if (dia_bloqueado and not horario_liberado) or horario_bloqueado:
                bloqueado = True


        if bloqueado:
            form.add_error("horario", "Este horário está bloqueado.")
        elif ja_existe:
            form.add_error("horario", "Esse horário já está ocupado para essa data.")
        elif form.is_valid():
            agendamento = form.save(commit=False)
            agendamento.cliente = cliente
            agendamento.servico = servico

            try:
                agendamento.full_clean()
                agendamento.save()

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

    bloqueados = []

    bloqueios = HorarioBloqueado.objects.none() 

    if data_convertida:
        bloqueios = HorarioBloqueado.objects.filter(data=data_convertida)

    dia_bloqueado = bloqueios.filter(
        horario__isnull=True,
        tipo='bloqueio'
    ).exists()

    for h in horarios:
        horario_time = datetime.strptime(h, "%H:%M").time()

        horario_bloqueado = bloqueios.filter(
            horario=horario_time,
            tipo='bloqueio'
        ).exists()

        horario_liberado = bloqueios.filter(
            horario=horario_time,
            tipo='liberado'
        ).exists()

        if (dia_bloqueado and not horario_liberado) or horario_bloqueado:
            bloqueados.append(h)

    return render(request, 'clients/agendar.html', {
        'form': form,
        'horarios': horarios,
        'horarios_ocupados': horarios_ocupados,
        'data_selecionada': data_selecionada,
        'servico': servico,
        'bloqueados': bloqueados,
    })

#Listar agendamentos
@login_required
def listar_agendamentos(request):

    cliente, _ = Cliente.objects.get_or_create(id_usuario=request.user)

    agendamentos = Agendamento.objects.filter(cliente=cliente).order_by('data', 'horario')

    return render(request, 'clients/lista.html', {
        'agendamentos': agendamentos
    })

@login_required
def excluir_agendamento(request, id):
    cliente, _ = Cliente.objects.get_or_create(id_usuario=request.user)

    agendamento = get_object_or_404(Agendamento, id=id, cliente=cliente)

    if request.method == 'POST':
        agendamento.delete()
        return redirect('listar_agendamentos')
    
    return render (request, 'clients/confirmar_exclusao.html', {
        'agendamento': agendamento
    })



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


def perfil(request):
    return render(request, 'clients/perfil.html')

def sobre(request):
    return render(request, 'clients/sobre.html')

def suporte(request):
    return render(request, 'clients/suporte.html')