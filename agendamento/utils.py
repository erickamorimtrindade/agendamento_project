from datetime import datetime, time

HORARIOS_POR_DIA = {
    0: [  # Segunda
        "08:00",
        "09:30",
        "13:00",
        "14:30",
        "16:00",
        "17:30",
        "19:00",
    ],

    1: [  # Terça
        "08:00",
        "09:30",
        "17:30",
        "19:00",
    ],

    2: [  # Quarta
        "08:00",
        "09:30",
        "13:00",
        "14:30",
        "16:00",
        "17:30",
        "19:00",
    ],

    3: [  # Quinta
        "08:00",
        "09:30",
        "13:00",
        "14:30",
        "16:00",
    ],

    4: [  # Sexta
        "08:00",
        "09:30",
        "13:00",
        "14:30",
        "16:00",
    ],

    5: [  # Sábado
        "08:00",
        "09:30",
        "13:00",
        "14:30",
    ],

    6: []  # Domingo fechado
}

def gerar_horarios(data):

    if not data:
        return []

    if isinstance(data, str):
        data = datetime.strptime(data, "%Y-%m-%d").date()

    return HORARIOS_POR_DIA.get(data.weekday(), [])


# Horário de exceção: às 09:30, o almoço cobre o tempo extra
HORARIO_EXCECAO_ALMOCO = time(9, 30)


def requer_horario_duplo(servico):
    """
    Retorna True se o serviço tiver o campo horario_duplo marcado como True.
    Independente do nome — basta marcar na hora de cadastrar o serviço.
    """
    if servico is None:
        return False
    return bool(getattr(servico, 'horario_duplo', False))


def get_proximo_horario(horario_str, lista_horarios):
    """
    Dado um horário no formato "HH:MM" e a lista de horários do dia,
    retorna o próximo horário da lista ou None se for o último.
    """
    try:
        idx = lista_horarios.index(horario_str)
    except ValueError:
        return None

    if idx + 1 < len(lista_horarios):
        return lista_horarios[idx + 1]

    return None  # É o último horário do dia


def is_excecao_almoco(horario_str):
    """
    Retorna True se o horário selecionado for 11:00 (exceção do almoço).
    """
    try:
        h = datetime.strptime(horario_str, "%H:%M").time()
        return h == HORARIO_EXCECAO_ALMOCO
    except (ValueError, TypeError):
        return False