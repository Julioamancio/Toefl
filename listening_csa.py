"""
Módulo para cálculo de CSA (Class-Specific Adjustment) para Listening
Implementação conforme especificações do PROMPT_MUDANCAS_CSA.md
"""

def get_listening_cefr(listening_score):
    """
    Determina o nível CEFR baseado na pontuação de listening TOEFL Junior (escala 200-300)
    """
    if listening_score is None:
        return None
    
    # Mapeamento de pontuações para níveis CEFR (escala TOEFL Junior 200-300)
    # Baseado na tabela oficial ETS para TOEFL Junior
    # Nota: A pontuação mínima é 200, então não existe A1 nesta escala
    if listening_score >= 290:
        return 'B2'
    elif listening_score >= 245:
        return 'B1'
    elif listening_score >= 210:
        return 'A2'
    else:
        # Para pontuações entre 200-209, ainda consideramos A2 (nível mínimo válido)
        return 'A2'

def calculate_proportional_csa_6th_grade(listening_score):
    """
    Cálculo proporcional para 6º ano (6.1, 6.2, 6.3)
    200 pontos = 3.0 CSA, 264 pontos = 5.0 CSA
    """
    if listening_score is None:
        return {"expected_level": "A2", "obtained_level": None, "points": 0.0}
    
    # Âncoras: 200 pontos = 3.0 CSA, 264 pontos = 5.0 CSA
    if listening_score >= 264:
        points = 5.0
    elif listening_score >= 200:
        # Proporcional entre 200-264 pontos (3.0-5.0 CSA)
        points = 3.0 + ((listening_score - 200) / (264 - 200)) * (5.0 - 3.0)
    else:
        # Proporcional abaixo de 200 pontos (0.0-3.0 CSA)
        points = (listening_score / 200) * 3.0
    
    # Obter nível CEFR obtido
    obtained_level = get_listening_cefr(listening_score)
    
    return {
        "expected_level": "A2",  # Nível esperado genérico para 6º ano
        "obtained_level": obtained_level,
        "points": round(points, 1)
    }

def calculate_proportional_csa_9_1(listening_score):
    """
    Cálculo proporcional para 9.1
    0 pontos = 0.0 CSA, 284 pontos = 5.0 CSA
    """
    if listening_score is None:
        return {"expected_level": "B2", "obtained_level": None, "points": 0.0}
    
    # Proporção linear: CSA = (score / 284) * 5.0
    if listening_score >= 284:
        points = 5.0
    else:
        points = (listening_score / 284) * 5.0
    
    # Obter nível CEFR obtido
    obtained_level = get_listening_cefr(listening_score)
    
    return {
        "expected_level": "B2",  # Nível esperado para 9.1
        "obtained_level": obtained_level,
        "points": round(points, 1)
    }

def calculate_step_based_csa_9th_grade(rotulo_escolar, listening_score):
    """
    Cálculo por degraus para 9.2 e 9.3
    Baseado na diferença entre CEFR obtido e esperado
    """
    if listening_score is None:
        return {"expected_level": "B2", "obtained_level": None, "points": 0.0}
    
    # Nível esperado para 9º ano
    expected_level = "B2"
    obtained_level = get_listening_cefr(listening_score)
    
    # Mapeamento de níveis CEFR para valores numéricos
    cefr_values = {
        'A1': 1,
        'A2': 2,
        'B1': 3,
        'B2': 4,
        'C1': 5,
        'C2': 6
    }
    
    expected_value = cefr_values.get(expected_level, 4)  # B2 = 4
    obtained_value = cefr_values.get(obtained_level, 1)  # Default A1 = 1
    
    # Calcular diferença
    difference = obtained_value - expected_value
    
    # Sistema de degraus baseado na diferença
    if difference >= 0:
        points = 5.0
    elif difference == -1:
        points = 4.0
    elif difference == -2:
        points = 3.0
    elif difference == -3:
        points = 2.0
    elif difference == -4:
        points = 1.0
    elif difference == -5:
        points = 1.0  # A1 STARTER vs B2
    else:  # difference < -5
        points = 0.0
    
    return {
        "expected_level": expected_level,
        "obtained_level": obtained_level,
        "points": points,
        "adjustment": difference  # Adicionar o campo adjustment
    }

def compute_listening_csa(rotulo_escolar, listening_score):
    """
    Função principal para cálculo de CSA
    Implementa diferentes lógicas conforme o rótulo escolar
    """
    if not rotulo_escolar or listening_score is None:
        return {
            'points': 0.0,
            'expected_level': None,
            'obtained_level': None,
            'adjustment': 0
        }
    
    # Normalizar o rótulo escolar
    rotulo_normalizado = str(rotulo_escolar).strip()
    
    # Verificar se é 6º ano (6.1, 6.2, 6.3)
    if rotulo_normalizado in ['6.1', '6.2', '6.3']:
        result = calculate_proportional_csa_6th_grade(listening_score)
    # Verificar se é 9.1 (cálculo proporcional especial)
    elif rotulo_normalizado == '9.1':
        result = calculate_proportional_csa_9_1(listening_score)
    # 9.2 e 9.3 usam cálculo por degraus
    elif rotulo_normalizado in ['9.2', '9.3']:
        result = calculate_step_based_csa_9th_grade(rotulo_normalizado, listening_score)
    else:
        # Rótulo não reconhecido
        return {
            'points': 0.0,
            'expected_level': rotulo_normalizado,
            'obtained_level': None,
            'adjustment': 0
        }
    
    # Manter compatibilidade com formato antigo
    return {
        'points': result['points'],
        'expected_level': result['expected_level'],
        'obtained_level': result['obtained_level'],
        'adjustment': result.get('adjustment', 0)  # Usar adjustment da função ou 0 como padrão
    }