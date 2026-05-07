from datetime import datetime

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