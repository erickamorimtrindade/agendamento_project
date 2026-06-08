from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Cliente, Agendamento, Servico, NotificacaoExclusao
from .forms import AgendamentoForm, IdentificarUsuarioForm , RedefinirSenhaForm
from datetime import datetime, timedelta, date
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.admin.views.decorators import staff_member_required
from collections import defaultdict
import json, re
from .models import HorarioBloqueado
from django.utils import timezone
from .utils import (
    gerar_horarios,
    requer_horario_duplo,
    get_proximo_horario,
    is_excecao_almoco,
    is_horario_dentro_24h,
)
from django.contrib import messages
from decimal import Decimal
import calendar
from django.http import JsonResponse

STATUS_VALIDOS = {'presente', 'ausente', 'pendente'}
#painel do adm --------

@staff_member_required
def criar_servico(request):
    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        descricao = request.POST.get("descricao", "").strip()
        preco = request.POST.get("preco", "").strip()
        duracao = request.POST.get("duracao_minutos", "").strip()
        horario_duplo = request.POST.get("horario_duplo") == "on"

        # 1. valida primeiro
        if not nome or not preco or not duracao:
            return render(request, "admin/criar_servico.html", {
                "erro": "Preencha todos os campos obrigatórios."
            })

        try:
            preco = float(preco)
            duracao = int(duracao)
        except ValueError:
            return render(request, "admin/criar_servico.html", {
                "erro": "Preço e duração devem ser numéricos."
            })

        # 2. só cria após validar
        Servico.objects.create(
            nome=nome,
            descricao=descricao,
            preco=preco,
            duracao_minutos=duracao,
            horario_duplo=horario_duplo,
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

        novo_duplo = request.POST.get("horario_duplo") == "on"
        era_duplo = servico.horario_duplo  # valor antes de salvar

        servico.horario_duplo = novo_duplo
        servico.save()

        # ── Sincroniza bloqueios retroativos para agendamentos futuros ──
        hoje = date.today()
        agendamentos_futuros = Agendamento.objects.filter(
            servico=servico,
            data__gte=hoje
        )

        for ag in agendamentos_futuros:
            horario_str = ag.horario.strftime("%H:%M")

            # Ignora exceção do almoço e último horário do dia
            if is_excecao_almoco(horario_str):
                continue

            horarios_do_dia = gerar_horarios(ag.data)
            proximo = get_proximo_horario(horario_str, horarios_do_dia)

            if proximo is None:
                continue  # último horário do dia, não bloqueia

            proximo_time = datetime.strptime(proximo, "%H:%M").time()

            if novo_duplo and not era_duplo:
                # Serviço virou duplo → cria bloqueio para o próximo horário
                # Só bloqueia se não houver agendamento real nesse horário
                proximo_tem_agendamento = Agendamento.objects.filter(
                    data=ag.data,
                    horario=proximo_time
                ).exists()
                if not proximo_tem_agendamento:
                    HorarioBloqueado.objects.update_or_create(
                        data=ag.data,
                        horario=proximo_time,
                        defaults={"tipo": "bloqueio"}
                    )

            elif era_duplo and not novo_duplo:
                # Serviço deixou de ser duplo → remove o bloqueio criado por ele
                HorarioBloqueado.objects.filter(
                    data=ag.data,
                    horario=proximo_time,
                    tipo="bloqueio"
                ).delete()
        # ────────────────────────────────────────────────────────────────

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
def calendario_admin(request):
    """
    Página principal do Calendário Administrativo.
    Renderiza a estrutura base; os dados vêm via AJAX (api_calendario_dados).
    """
    hoje = date.today()
    return render(request, 'admin/calendario_admin.html', {
        'hoje': hoje.isoformat(),
    })


@staff_member_required
def api_calendario_dados(request):
    """
    Endpoint JSON — retorna dados do mês solicitado.
    Parâmetros GET: ano (int), mes (int)

    Resposta:
    {
        "dias": {
            "2025-06-10": {
                "total": 3,
                "agendamentos": [...],
                "horarios": [
                    {"horario": "08:00", "status": "livre|ocupado|bloqueado", "agendamento": {...}|null},
                    ...
                ]
            }
        }
    }
    """
    try:
        ano = int(request.GET.get('ano', date.today().year))
        mes = int(request.GET.get('mes', date.today().month))
    except (ValueError, TypeError):
        return JsonResponse({'erro': 'Parâmetros inválidos'}, status=400)

    # Primeiro e último dia do mês
    primeiro_dia = date(ano, mes, 1)
    ultimo_dia = date(ano, mes, calendar.monthrange(ano, mes)[1])

    # ── Busca todos os agendamentos do mês em uma única query ──
    agendamentos_mes = (
        Agendamento.objects
        .filter(data__gte=primeiro_dia, data__lte=ultimo_dia)
        .select_related('cliente__id_usuario', 'servico')
        .order_by('data', 'horario')
    )

    # ── Busca todos os bloqueios do mês em uma única query ──
    bloqueios_mes = (
        HorarioBloqueado.objects
        .filter(data__gte=primeiro_dia, data__lte=ultimo_dia)
    )

    # Indexa agendamentos por (data, horario)
    agenda_idx = {}  # key: (data_str, horario_str) → agendamento_dict
    contagem_por_dia = defaultdict(int)

    for ag in agendamentos_mes:
        data_str = ag.data.isoformat()
        hora_str = ag.horario.strftime('%H:%M')
        contagem_por_dia[data_str] += 1
        agenda_idx[(data_str, hora_str)] = {
            'id': ag.id,
            'cliente': ag.cliente.id_usuario.get_full_name() or ag.cliente.id_usuario.username,
            'telefone': ag.cliente.telefone,
            'servico': ag.servico.nome if ag.servico else '—',
            'status': ag.status,
            'descricao': ag.descricao,
        }

    # Indexa bloqueios por (data, horario)  — horario None = dia inteiro bloqueado
    bloqueio_idx = {}  # key: (data_str, horario_str|None) → tipo
    dias_bloqueados = set()  # dias com bloqueio de dia inteiro

    for b in bloqueios_mes:
        data_str = b.data.isoformat()
        if b.horario is None:
            if b.tipo == 'bloqueio':
                dias_bloqueados.add(data_str)
        else:
            hora_str = b.horario.strftime('%H:%M')
            bloqueio_idx[(data_str, hora_str)] = b.tipo  # 'bloqueio' ou 'liberado'

    # ── Monta a estrutura de resposta dia a dia ──
    dias = {}
    delta = timedelta(days=1)
    dia_cursor = primeiro_dia

    while dia_cursor <= ultimo_dia:
        data_str = dia_cursor.isoformat()
        horarios_do_dia = gerar_horarios(dia_cursor)  # lista ["08:00", ...]
        dia_bloqueado = data_str in dias_bloqueados

        slots = []
        for hora_str in horarios_do_dia:
            ag = agenda_idx.get((data_str, hora_str))
            tipo_bloqueio = bloqueio_idx.get((data_str, hora_str))

            if ag:
                status_slot = 'ocupado'
            elif dia_bloqueado:
                # Se o dia está bloqueado mas existe uma exceção (liberado), fica livre
                if tipo_bloqueio == 'liberado':
                    status_slot = 'livre'
                else:
                    status_slot = 'bloqueado'
            elif tipo_bloqueio == 'bloqueio':
                status_slot = 'bloqueado'
            else:
                status_slot = 'livre'

            slots.append({
                'horario': hora_str,
                'status': status_slot,
                'agendamento': ag,
            })

        total_agendamentos = contagem_por_dia.get(data_str, 0)
        total_horarios = len(horarios_do_dia)

        dias[data_str] = {
            'total': total_agendamentos,
            'total_horarios': total_horarios,
            'fechado': total_horarios == 0,
            'dia_bloqueado': dia_bloqueado,
            'horarios': slots,
        }

        dia_cursor += delta

    return JsonResponse({
        'ano': ano,
        'mes': mes,
        'dias': dias,
    })

@staff_member_required
def relatorio_31_dias(request):
    hoje = timezone.localdate()
    inicio = hoje - timedelta(days=30) 

    agendamentos = Agendamento.objects.filter(
        data__range=[inicio, hoje],
        status='presente'
    ).select_related('servico').order_by('data')

    total = sum(ag.servico.preco for ag in agendamentos)

    faturamento_por_dia = defaultdict(Decimal)

    for ag in agendamentos:
        faturamento_por_dia[ag.data.isoformat()] += ag.servico.preco

    datas_ordenadas = []
    valores_ordenados = []

    for i in range(0, 31):
        dia = inicio + timedelta(days=i)
        dia_str = dia.isoformat()

        datas_ordenadas.append(dia.strftime("%d/%m"))
        valores_ordenados.append(float(round(faturamento_por_dia.get(dia_str, Decimal('0')), 2)))

    
    servicos = Servico.objects.all()
    servicos_dict = {s.nome: Decimal('0') for s in servicos}

    for ag in agendamentos:
        servicos_dict[ag.servico.nome] += ag.servico.preco

    servicos_dict = {k: v for k, v in servicos_dict.items() if v > 0}

    servicos_labels = list(servicos_dict.keys())
    servicos_valores = [float(v) for v in servicos_dict.values()]

    
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
    if status not in STATUS_VALIDOS:
        messages.error(request, "Status inválido.")
        return redirect('agendamentos_hoje')

    ag = get_object_or_404(Agendamento, id=id)
    ag.status = status
    ag.save()
    return redirect('agendamentos_hoje')

@staff_member_required
def proximos_agendamentos(request):

    data = request.GET.get("data")

    data_convertida = None

    data_convertida = converter_data(data) if data else None

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


@staff_member_required
def excluir_agendamento_admin(request, id):
    """
    Exclusão de agendamento pelo administrador.
    Cria uma NotificacaoExclusao para a cliente afetada.
    Só aceita POST para evitar exclusões acidentais via GET.
    """
    agendamento = get_object_or_404(Agendamento, id=id)

    if request.method == 'POST':
        cliente = agendamento.cliente
        servico_nome = agendamento.servico.nome if agendamento.servico else 'Serviço não informado'
        data_ag = agendamento.data
        horario_ag = agendamento.horario

        # Remove bloqueio do horário duplo, se houver
        if agendamento.servico and requer_horario_duplo(agendamento.servico):
            horario_str = agendamento.horario.strftime("%H:%M")
            if not is_excecao_almoco(horario_str):
                horarios_do_dia = gerar_horarios(agendamento.data)
                proximo = get_proximo_horario(horario_str, horarios_do_dia)
                if proximo is not None:
                    proximo_time = datetime.strptime(proximo, "%H:%M").time()
                    HorarioBloqueado.objects.filter(
                        data=agendamento.data,
                        horario=proximo_time,
                        tipo="bloqueio"
                    ).delete()

        # Salva os dados ANTES de deletar
        agendamento.delete()

        # Cria a notificação para a cliente
        NotificacaoExclusao.objects.create(
            cliente=cliente,
            servico_nome=servico_nome,
            data_agendamento=data_ag,
            horario_agendamento=horario_ag,
        )

        messages.success(request, 'Agendamento excluído e cliente notificada.')
        return redirect('proximos_agendamentos')

    # GET — exibe confirmação
    return render(request, 'admin/confirmar_exclusao_agendamento.html', {
        'agendamento': agendamento
    })


@login_required
def marcar_notificacao_lida(request, notif_id):
    """
    Marca uma NotificacaoExclusao como visualizada (chamada via POST/AJAX).
    Só o próprio cliente dono da notificação pode marcá-la.
    """
    if request.method == 'POST':
        cliente = get_object_or_404(Cliente, id_usuario=request.user)
        notif = get_object_or_404(NotificacaoExclusao, id=notif_id, cliente=cliente)
        notif.visualizado = True
        notif.save()
        from django.http import JsonResponse
        return JsonResponse({'ok': True})
    from django.http import JsonResponse
    return JsonResponse({'ok': False}, status=405)


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

    horarios = gerar_horarios(data_formatada)

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

        if data_formatada and data_formatada >= date.today():
            HorarioBloqueado.objects.filter(
                data=data_formatada,
                horario=None,
                tipo="bloqueio"
            ).delete()

        return redirect(f"/gerenciar-horarios/?data={data}")

    return redirect("/gerenciar-horarios/")

@staff_member_required
def remover_excecao(request):
    if request.method == "POST":
        data = request.POST.get("data")
        horario = request.POST.get("horario")

        data_formatada = converter_data(data)

        if data_formatada and horario:
            horario_formatado = datetime.strptime(horario, "%H:%M").time()

            HorarioBloqueado.objects.filter(
                data=data_formatada,
                horario=horario_formatado,
                tipo="liberado"
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

        return render(request, 'clients/login.html', {'erro': 'Login inválido! Verifique os dados da conta ou Crie uma!'})

    return render(request, 'clients/login.html')

#Logout
def logout_view(request):
    logout(request)
    return redirect('login')

#Campo "Esqueci minha senha"
def esqueci_senha(request):
    form = IdentificarUsuarioForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        nome = form.cleaned_data["nome"]
        telefone = form.cleaned_data["telefone"]

        usuario = User.objects.filter(username__iexact=nome).first()

        def apenas_digitos(valor):
            return re.sub(r'\D', '', valor or '')

        telefone_confere = (
            usuario is not None
            and hasattr(usuario, 'cliente')
            and apenas_digitos(usuario.cliente.telefone) == apenas_digitos(telefone)
        )

        if not telefone_confere:
            form.add_error(None, "Dados não encontrados. Verifique nome e telefone.")
            return render(request, "clients/esqueci_senha.html", {"form": form})

        request.session["redefinir_nome"] = usuario.username
        return redirect("redefinir_senha")

    return render(request, "clients/esqueci_senha.html", {"form": form})

def redefinir_senha(request):
    nome = request.session.get("redefinir_nome")

    if not nome:
        messages.error(request, "Sessão expirada. Comece novamente.")
        return redirect("esqueci_senha")

    form = RedefinirSenhaForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        nova_senha = form.cleaned_data["nova_senha"]
        usuario = User.objects.filter(username__iexact=nome).first()

        if usuario:
            usuario.set_password(nova_senha)
            usuario.save()
            del request.session["redefinir_nome"]
            messages.success(request, "Senha redefinida com sucesso! Pressione o botão 'Voltar para o login' e entre com sua nova senha!")
            #return redirect("login")
        else:
            messages.error(request, "Usuário não encontrado.")
            return redirect("esqueci_senha")

    return render(request, "clients/redefinir_senha.html", {"form": form, "nome": nome})

#Home
@login_required
def home(request):
    if request.user.is_staff:
        return redirect('painel_admin')  # admin vai pro painel

    notificacoes_pendentes = []
    if request.user.is_authenticated:
        try:
            cliente = Cliente.objects.get(id_usuario=request.user)
            notificacoes_pendentes = list(
                NotificacaoExclusao.objects.filter(cliente=cliente, visualizado=False)
                .order_by('criado_em')
            )
        except Cliente.DoesNotExist:
            pass

    return render(request, 'clients/home.html', {
        'notificacoes_pendentes': notificacoes_pendentes
    })

#Criar agendamentos
@login_required
def criar_agendamento(request):

    if request.user.is_staff:
        return redirect('painel_admin')

    cliente, _ = Cliente.objects.get_or_create(id_usuario=request.user)

    # ── Bloqueio de cliente ─────────────────────────────────────────────
    if cliente.bloqueado:
        return render(request, 'clients/cliente_bloqueado.html')
    # ───────────────────────────────────────────────────────────────────

    servico_id = request.session.get("servico_id")

    if not servico_id:
        return redirect("escolher_servico")

    servico = get_object_or_404(Servico, id=servico_id, ativo=True)

    # Detecta se esse serviço precisa de dois horários consecutivos
    duplo = requer_horario_duplo(servico)

    data_selecionada = request.GET.get("data") or request.POST.get("data")
    data_convertida = converter_data(data_selecionada)

    horarios = gerar_horarios(data_convertida)
    horarios_ocupados = []

    if data_convertida:
        agendamentos_do_dia = Agendamento.objects.filter(data=data_convertida)
        horarios_ocupados = [
            ag.horario.strftime("%H:%M") for ag in agendamentos_do_dia
        ]

    # ─── CONSULTA ÚNICA — reutilizada em todo o resto da view ───
    bloqueios = (
        HorarioBloqueado.objects.filter(data=data_convertida)
        if data_convertida
        else HorarioBloqueado.objects.none()
    )

    dia_bloqueado = bloqueios.filter(
        horario__isnull=True,
        tipo='bloqueio'
    ).exists()
    # ────────────────────────────────────────────────────────────

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

        # ── Validação do horário duplo ──────────────────────────────────
        erro_duplo = None
        if duplo and horario_selecionado and data_convertida and not bloqueado and not ja_existe:
            if not is_excecao_almoco(horario_selecionado):
                proximo = get_proximo_horario(horario_selecionado, horarios)

                if proximo is not None:
                    # Verifica se o próximo está ocupado por agendamento
                    proximo_ocupado_ag = Agendamento.objects.filter(
                        data=data_convertida,
                        horario=datetime.strptime(proximo, "%H:%M").time()
                    ).exists()

                    # Verifica se o próximo está bloqueado manualmente
                    proximo_time = datetime.strptime(proximo, "%H:%M").time()
                    proximo_bloqueado_manual = bloqueios.filter(
                        horario=proximo_time,
                        tipo='bloqueio'
                    ).exists()
                    proximo_liberado_manual = bloqueios.filter(
                        horario=proximo_time,
                        tipo='liberado'
                    ).exists()
                    proximo_bloqueado = (
                        proximo_ocupado_ag
                        or ((dia_bloqueado and not proximo_liberado_manual) or proximo_bloqueado_manual)
                    )

                    if proximo_bloqueado:
                        erro_duplo = (
                            f"Este serviço ocupa dois horários consecutivos "
                            f"({horario_selecionado} e {proximo}), "
                            f"mas {proximo} já está ocupado. Escolha outro horário."
                        )
                # Se proximo is None = último horário do dia → pode agendar normalmente
        # ────────────────────────────────────────────────────────────────
        if bloqueado:
            form.add_error("horario", "Este horário está bloqueado.")
        elif ja_existe:
            form.add_error("horario", "Esse horário já está ocupado para essa data.")
        elif erro_duplo:
            form.add_error("horario", erro_duplo)
        elif data_convertida and horario_selecionado and is_horario_dentro_24h(data_convertida, horario_selecionado):
            # ── Validação de antecedência mínima (24h) — camada da view ──
            from datetime import timedelta
            limite = timezone.localtime() + timedelta(hours=24)
            form.add_error(
                "horario",
                f"Agendamentos devem ser feitos com pelo menos 24 horas de antecedência. "
                f"O horário mais cedo disponível é {limite.strftime('%d/%m/%Y às %H:%M')}."
            )
            # ─────────────────────────────────────────────────────────────        
        elif form.is_valid():
            agendamento = form.save(commit=False)
            agendamento.cliente = cliente
            agendamento.servico = servico

            try:
                agendamento.full_clean()
                agendamento.save()

                # ── Se for serviço duplo, bloqueia o próximo horário ──
                if duplo and not is_excecao_almoco(horario_selecionado):
                    proximo = get_proximo_horario(horario_selecionado, horarios)
                    if proximo is not None:
                        proximo_time = datetime.strptime(proximo, "%H:%M").time()
                        HorarioBloqueado.objects.update_or_create(
                            data=data_convertida,
                            horario=proximo_time,
                            defaults={"tipo": "bloqueio"}
                        )
                # ─────────────────────────────────────────────────────

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

    # ── Monta lista de horários indisponíveis para o template ──────────
    # Inclui: ocupados por agendamento, bloqueados manualmente,
    # dentro das próximas 24h (regra de antecedência mínima),
    # e horários anteriores que ficariam inválidos por causa do duplo.
    bloqueados = []
    horarios_menos_24h = []

    for h in horarios:
        horario_time = datetime.strptime(h, "%H:%M").time()

        # ── Regra de antecedência mínima de 24h ──
        if data_convertida and is_horario_dentro_24h(data_convertida, h):
            horarios_menos_24h.append(h)
            continue
        # ─────────────────────────────────────────

        horario_bloqueado_manual = bloqueios.filter(
            horario=horario_time,
            tipo='bloqueio'
        ).exists()

        horario_liberado_manual = bloqueios.filter(
            horario=horario_time,
            tipo='liberado'
        ).exists()

        if (dia_bloqueado and not horario_liberado_manual) or horario_bloqueado_manual:
            bloqueados.append(h)
        elif duplo and not is_excecao_almoco(h):
            # Se for serviço duplo: verifica se o PRÓXIMO está ocupado/bloqueado
            # para marcar o horário ATUAL como indisponível
            proximo = get_proximo_horario(h, horarios)

            if proximo is not None:
                proximo_time = datetime.strptime(proximo, "%H:%M").time()

                proximo_bloq_manual = bloqueios.filter(
                    horario=proximo_time,
                    tipo='bloqueio'
                ).exists()
                proximo_lib_manual = bloqueios.filter(
                    horario=proximo_time,
                    tipo='liberado'
                ).exists()
                proximo_ocupado_ag = proximo in horarios_ocupados
                proximo_indisponivel = (
                    proximo_ocupado_ag
                    or ((dia_bloqueado and not proximo_lib_manual) or proximo_bloq_manual)
                )

                if proximo_indisponivel:
                    bloqueados.append(h)
            # Se proximo is None = último horário → não bloqueia (regra do último horário)
    # ────────────────────────────────────────────────────────────────────

    return render(request, 'clients/agendar.html', {
        'form': form,
        'horarios': horarios,
        'horarios_ocupados': horarios_ocupados,
        'data_selecionada': data_selecionada,
        'servico': servico,
        'bloqueados': bloqueados,
        'duplo': duplo,
        'horarios_menos_24h': horarios_menos_24h,
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
        # ── Se era serviço duplo, remove o bloqueio do próximo horário ──
        if agendamento.servico and requer_horario_duplo(agendamento.servico):
            horario_str = agendamento.horario.strftime("%H:%M")
            if not is_excecao_almoco(horario_str):
                horarios_do_dia = gerar_horarios(agendamento.data)
                proximo = get_proximo_horario(horario_str, horarios_do_dia)
                if proximo is not None:
                    proximo_time = datetime.strptime(proximo, "%H:%M").time()
                    HorarioBloqueado.objects.filter(
                        data=agendamento.data,
                        horario=proximo_time,
                        tipo="bloqueio"
                    ).delete()
        # ────────────────────────────────────────────────────────────────

        agendamento.delete()
        return redirect('listar_agendamentos')
    
    return render(request, 'clients/confirmar_exclusao.html', {
        'agendamento': agendamento
    })

@login_required
def escolher_servico(request):
    servicos = Servico.objects.filter(ativo=True)
    erro = None

    # Bloqueia cliente impedido de agendar
    cliente, _ = Cliente.objects.get_or_create(id_usuario=request.user)
    if cliente.bloqueado:
        return render(request, 'clients/cliente_bloqueado.html')
    
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

# ── GESTÃO DE CLIENTES (admin) ────────────────────────────────────────────────

@staff_member_required
def listar_clientes(request):
    """
    Painel administrativo de clientes.
    Exibe nome, telefone, total de agendamentos, total de ausências,
    status de bloqueio e data de cadastro.
    Suporta busca por nome via query string ?q=.
    """
    q = request.GET.get('q', '').strip()

    clientes_qs = Cliente.objects.select_related('id_usuario').all()

    if q:
        clientes_qs = clientes_qs.filter(id_usuario__username__icontains=q)

    clientes_qs = clientes_qs.order_by('id_usuario__username')

    clientes_data = []
    for cliente in clientes_qs:
        total_agendamentos = Agendamento.objects.filter(cliente=cliente).count()
        total_ausencias = Agendamento.objects.filter(cliente=cliente, status='ausente').count()
        clientes_data.append({
            'cliente': cliente,
            'total_agendamentos': total_agendamentos,
            'total_ausencias': total_ausencias,
        })

    return render(request, 'admin/listar_clientes.html', {
        'clientes_data': clientes_data,
        'q': q,
        'total_clientes': clientes_qs.count(),
    })


@staff_member_required
def bloquear_cliente(request, user_id):
    """Bloqueia um cliente, impedindo novos agendamentos."""
    if request.method == 'POST':
        cliente = get_object_or_404(Cliente, id_usuario__id=user_id)
        # Nunca bloqueia staff/admin
        if not cliente.id_usuario.is_staff:
            cliente.bloqueado = True
            cliente.save()
            messages.success(
                request,
                f'Cliente "{cliente.id_usuario.username}" foi bloqueado com sucesso.'
            )
        else:
            messages.error(request, 'Não é possível bloquear um administrador.')
    return redirect('listar_clientes')


@staff_member_required
def desbloquear_cliente(request, user_id):
    """Desbloqueia um cliente previamente bloqueado."""
    if request.method == 'POST':
        cliente = get_object_or_404(Cliente, id_usuario__id=user_id)
        cliente.bloqueado = False
        cliente.save()
        messages.success(
            request,
            f'Cliente "{cliente.id_usuario.username}" foi desbloqueado com sucesso.'
        )
    return redirect('listar_clientes')


@staff_member_required
def excluir_cliente(request, user_id):
    """
    Exclui um cliente e sua conta de usuário.
    Todos os agendamentos são removidos em cascata pelo ORM (CASCADE no FK).
    Exige confirmação via POST para evitar exclusões acidentais.
    """
    user = get_object_or_404(User, id=user_id, is_staff=False)

    if request.method == 'POST':
        username = user.username
        # Deleta o User — o Cliente e os Agendamentos são removidos em cascata
        user.delete()
        messages.success(request, f'Conta de "{username}" foi excluída com sucesso.')
        return redirect('listar_clientes')

    # GET → página de confirmação
    cliente = get_object_or_404(Cliente, id_usuario=user)
    total_agendamentos = Agendamento.objects.filter(cliente=cliente).count()
    return render(request, 'admin/confirmar_exclusao_cliente.html', {
        'user': user,
        'cliente': cliente,
        'total_agendamentos': total_agendamentos,
    })

# ──────────────────────────────────────────────────────────────────────────────

@login_required
def perfil(request):
    return render(request, 'clients/perfil.html')

@login_required
def sobre(request):
    return render(request, 'clients/sobre.html')

@login_required
def suporte(request):
    return render(request, 'clients/suporte.html')

def tutorial(request):
    return render(request, 'clients/tutorial.html')