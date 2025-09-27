"""
Configurações para o sistema de classificação TOEFL Junior
Sistema atualizado com subfaixas e cálculo proporcional
"""

# Faixas de pontuação CEFR para Listening (200-300)
CEFR_LISTENING_RANGES = {
    'A1': (0, 199),            # Abaixo de 200
    'A2': (200, 245),          # 200-245 (alinhado com school_label)
    'A2+': (246, 265),         # 246-265
    'B1': (266, 285),          # 266-285
    'B2': (286, 300),          # 286-300 (pontuação máxima)
    'B2+': (301, 311)          # Acima de 300 (teórico)
}

# Mapeamento de rótulos escolares
SCHOOL_LABELS = {
    'A1': '6.1',
    'A2': '6.2',
    'A2+': '6.3',
    'B1': '9.1',
    'B2': '9.2',
    'B2+': '9.3'
}

# Subfaixas para cálculo proporcional
SUBFAIXAS = {
    '6.1': {'min': 0, 'max': 199, 'cefr': 'A1'},
    '6.2': {'min': 200, 'max': 245, 'cefr': 'A2'},      # Alinhado com CEFR_LISTENING_RANGES
    '6.3': {'min': 246, 'max': 285, 'cefr': 'A2+'},     # Alinhado com school_label
    '9.1': {'min': 286, 'max': 299, 'cefr': 'B1'},      # Alinhado com school_label
    '9.2': {'min': 300, 'max': 310, 'cefr': 'B2'},      # Alinhado com school_label
    '9.3': {'min': 311, 'max': 350, 'cefr': 'B2+'}      # Teórico, acima do máximo
}

# Sistema floors_caps para cálculo de notas por meta
FLOORS_CAPS = {
    "6.1": {  # meta A1
        "6.1": {"floor": 4.0, "cap": 5.0},  # A1 → 4.0–5.0
        "6.2": {"floor": 5.0, "cap": 5.0},  # A2 → 5.0
        "6.3": {"floor": 5.0, "cap": 5.0},  # A2+ → 5.0
        "9.1": {"floor": 5.0, "cap": 5.0},  # B1 → 5.0
        "9.2": {"floor": 5.0, "cap": 5.0},  # B2 → 5.0
        "9.3": {"floor": 5.0, "cap": 5.0}   # B2+ → 5.0
    },
    "6.2": {  # meta A2
        "6.1": {"floor": 2.0, "cap": 3.0},  # A1 → 2.0–3.0
        "6.2": {"floor": 4.0, "cap": 5.0},  # A2 → 4.0–5.0
        "6.3": {"floor": 5.0, "cap": 5.0},  # A2+ → 5.0
        "9.1": {"floor": 5.0, "cap": 5.0},  # B1 → 5.0
        "9.2": {"floor": 5.0, "cap": 5.0},  # B2 → 5.0
        "9.3": {"floor": 5.0, "cap": 5.0}   # B2+ → 5.0
    },
    "6.3": {  # meta A2+
        "6.1": {"floor": 2.0, "cap": 2.5},  # A1 → 2.0–2.5
        "6.2": {"floor": 3.0, "cap": 4.0},  # A2 → 3.0–4.0
        "6.3": {"floor": 4.0, "cap": 5.0},  # A2+ → 4.0–5.0
        "9.1": {"floor": 5.0, "cap": 5.0},  # B1 → 5.0
        "9.2": {"floor": 5.0, "cap": 5.0},  # B2 → 5.0
        "9.3": {"floor": 5.0, "cap": 5.0}   # B2+ → 5.0
    },
    "9.1": {  # meta B1
        "6.1": {"floor": 1.0, "cap": 2.0},  # A1 → 1.0–2.0
        "6.2": {"floor": 2.0, "cap": 3.0},  # A2 → 2.0–3.0
        "6.3": {"floor": 3.0, "cap": 4.0},  # A2+ → 3.0–4.0
        "9.1": {"floor": 4.0, "cap": 5.0},  # B1 → 4.0–5.0
        "9.2": {"floor": 5.0, "cap": 5.0},  # B2 → 5.0
        "9.3": {"floor": 5.0, "cap": 5.0}   # B2+ → 5.0
    },
    "9.2": {  # meta B2
        "6.1": {"floor": 1.0, "cap": 1.5},  # A1 → 1.0–1.5
        "6.2": {"floor": 1.5, "cap": 2.5},  # A2 → 1.5–2.5
        "6.3": {"floor": 2.5, "cap": 3.5},  # A2+ → 2.5–3.5
        "9.1": {"floor": 3.5, "cap": 4.5},  # B1 → 3.5–4.5
        "9.2": {"floor": 4.0, "cap": 5.0},  # B2 → 4.0–5.0
        "9.3": {"floor": 5.0, "cap": 5.0}   # B2+ → 5.0
    },
    "9.3": {  # meta B2+
        "6.1": {"floor": 1.0, "cap": 1.0},  # A1 → 1.0
        "6.2": {"floor": 1.0, "cap": 2.0},  # A2 → 1.0–2.0
        "6.3": {"floor": 2.0, "cap": 3.0},  # A2+ → 2.0–3.0
        "9.1": {"floor": 3.0, "cap": 4.0},  # B1 → 3.0–4.0
        "9.2": {"floor": 4.0, "cap": 4.5},  # B2 → 4.0–4.5
        "9.3": {"floor": 4.5, "cap": 5.0}   # B2+ → 4.5–5.0
    }
}

# Configurações de cálculo de notas
GRADE_CONFIG = {
    'max_points': 5.0,
    'precision': 2  # casas decimais
}

# Ordem hierárquica dos rótulos escolares (do menor para o maior)
SCHOOL_LABEL_ORDER = ['6.1', '6.2', '6.3', '9.1', '9.2', '9.3']

def get_cefr_listening_ranges():
    """Retorna as faixas CEFR para Listening"""
    return CEFR_LISTENING_RANGES.copy()

def get_school_labels():
    """Retorna o mapeamento de rótulos escolares"""
    return SCHOOL_LABELS.copy()

def get_subfaixas():
    """Retorna as subfaixas para cálculo proporcional"""
    return SUBFAIXAS.copy()

def get_floors_caps():
    """Retorna o sistema floors_caps"""
    return FLOORS_CAPS.copy()

def get_grade_config():
    """Retorna as configurações de cálculo de notas"""
    return GRADE_CONFIG.copy()

def get_school_label_order():
    """Retorna a ordem hierárquica dos rótulos escolares"""
    return SCHOOL_LABEL_ORDER.copy()