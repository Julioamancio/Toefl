"""
Módulo para cálculo do Listening CSA (Competency-based Student Assessment)
"""

def compute_listening_csa(rotulo_escolar, listening_score):
    """
    Calcula a pontuação Listening CSA baseada no rótulo escolar e pontuação de listening.
    
    Args:
        rotulo_escolar (float or str): Rótulo escolar do estudante (ex: 6.1, 6.2, 9.1, etc.)
        listening_score (int): Pontuação de listening (0-300)
    
    Returns:
        dict: {
            "expected_level": str,  # Nível CEFR esperado baseado no rótulo escolar
            "obtained_level": str,  # Nível CEFR obtido baseado na pontuação
            "points": float        # Pontos CSA (0.0-5.0)
        }
    """
    
    # Converter rotulo_escolar para float se for string
    if isinstance(rotulo_escolar, str):
        try:
            rotulo_escolar = float(rotulo_escolar)
        except (ValueError, TypeError):
            return {
                "expected_level": None,
                "obtained_level": None,
                "points": 0.0
            }
    
    # Verificar se é 6º ano (6.1, 6.2, 6.3) - usa cálculo proporcional
    if rotulo_escolar in [6.1, 6.2, 6.3]:
        return calculate_proportional_csa_6th_grade(rotulo_escolar, listening_score)
    else:
        # 9º ano (9.1, 9.2, 9.3) - mantém cálculo por degraus
        return calculate_step_based_csa_9th_grade(rotulo_escolar, listening_score)


def calculate_proportional_csa_6th_grade(rotulo_escolar, listening_score):
    """
    Cálculo proporcional para alunos do 6º ano (6.1, 6.2, 6.3).
    200 pontos = 3.0 CSA, 264 pontos = 5.0 CSA
    """
    # Mapa Rótulo Escolar → CEFR esperado para 6º ano
    rotulo_to_cefr = {
        6.1: "A1 STARTER",
        6.2: "A1",
        6.3: "A2"
    }
    
    expected_level = rotulo_to_cefr.get(rotulo_escolar)
    
    if listening_score is None:
        return {
            "expected_level": expected_level,
            "obtained_level": None,
            "points": 0.0
        }
    
    # Obter nível CEFR obtido
    obtained_level = get_listening_cefr(listening_score)
    
    # Cálculo proporcional para 6º ano
    # Âncoras: 200 pontos = 3.0 CSA, 264 pontos = 5.0 CSA
    if listening_score >= 264:
        points = 5.0
    elif listening_score >= 200:
        # Proporcional entre 200-264 pontos (3.0-5.0 CSA)
        points = 3.0 + ((listening_score - 200) / (264 - 200)) * (5.0 - 3.0)
    else:
        # Proporcional abaixo de 200 pontos (0.0-3.0 CSA)
        points = (listening_score / 200) * 3.0
    
    # Garantir que não ultrapasse os limites
    points = max(0.0, min(5.0, points))
    
    return {
        "expected_level": expected_level,
        "obtained_level": obtained_level,
        "points": round(points, 1)
    }


def calculate_step_based_csa_9th_grade(rotulo_escolar, listening_score):
    """
    Calcula CSA de Listening para 9º ano.
    - 9.1: Método proporcional (284 pontos = 5.0 CSA, 200 pontos = 3.0 CSA)
    - 9.2 e 9.3: Método baseado em degraus (diferença entre níveis CEFR)
    """
    # Para 9.1, usar cálculo proporcional como o 6º ano
    if rotulo_escolar == 9.1:
        return calculate_proportional_csa_9_1(listening_score)
    
    # Para 9.2 e 9.3, manter o cálculo baseado em degraus
    # Mapa Rótulo Escolar → CEFR esperado para 9º ano
    rotulo_to_cefr = {
        9.2: "B2",
        9.3: "B2"  # Teto B2 para Listening
    }
    
    # Hierarquia de níveis CEFR para comparação
    cefr_hierarchy = {
        "A1 STARTER": 0,
        "A1": 1,
        "A2": 2,
        "A2+": 3,
        "B1": 4,
        "B2": 5
    }
    
    # Obter nível esperado
    expected_level = rotulo_to_cefr.get(rotulo_escolar)
    if expected_level is None:
        return {
            "expected_level": None,
            "obtained_level": None,
            "points": 0.0
        }
    
    # Obter nível obtido
    obtained_level = get_listening_cefr(listening_score)
    if obtained_level is None:
        return {
            "expected_level": expected_level,
            "obtained_level": None,
            "points": 0.0
        }
    
    # Calcular diferença de níveis
    expected_rank = cefr_hierarchy.get(expected_level, 0)
    obtained_rank = cefr_hierarchy.get(obtained_level, 0)
    
    # dif = idx(obtido) - idx(alvo_cefr)
    level_difference = obtained_rank - expected_rank
    
    # Pontuação base por degraus
    if level_difference >= 0:  # dif ≥ 0 ⇒ 5.0
        points = 5.0
    elif level_difference == -1:  # dif = -1 ⇒ 4.0
        points = 4.0
    elif level_difference == -2:  # dif = -2 ⇒ 3.0
        points = 3.0
    elif level_difference == -3:  # dif = -3 ⇒ 2.0
        points = 2.0
    elif level_difference == -4:  # dif = -4 ⇒ 1.0
        points = 1.0
    elif level_difference == -5:  # dif = -5 ⇒ 1.0 (A1 STARTER vs B2)
        points = 1.0
    else:  # dif < -5 ⇒ 0.0
        points = 0.0
    
    return {
        "expected_level": expected_level,
        "obtained_level": obtained_level,
        "points": points
    }


def calculate_proportional_csa_9_1(listening_score):
    """
    Calcula CSA de Listening para 9.1 usando método proporcional.
    284 pontos = 5.0 CSA, com proporção linear a partir de 0 pontos = 0.0 CSA.
    """
    if listening_score is None:
        return {
            "expected_level": "B1",
            "obtained_level": None,
            "points": 0.0
        }
    
    # Obter nível CEFR obtido
    obtained_level = get_listening_cefr(listening_score)
    
    # Cálculo proporcional: 284 pontos = 5.0 CSA, 0 pontos = 0.0 CSA
    if listening_score >= 284:
        points = 5.0
    elif listening_score > 0:
        # Proporção linear entre 0 (0.0) e 284 (5.0)
        # CSA = (score / 284) * 5.0
        points = (listening_score / 284) * 5.0
        points = min(points, 5.0)  # Cap em 5.0
    else:
        # 0 pontos = 0.0 CSA
        points = 0.0
    
    return {
        "expected_level": "B1",
        "obtained_level": obtained_level,
        "points": round(points, 2)
    }


def get_listening_cefr(score):
    """
    Converte pontuação de Listening para nível CEFR obtido.
    Função auxiliar usada por ambos os métodos de cálculo.
    """
    if score is None:
        return None
    
    # Âncoras específicas
    if score == 50:
        return "A1 STARTER"
    elif score == 100:
        return "A1"
    
    # Faixas de pontuação
    if 0 <= score <= 199:
        return "A1 STARTER"
    elif 200 <= score <= 239:
        return "A2"
    elif 240 <= score <= 264:
        return "A2+"
    elif 265 <= score <= 284:
        return "B1"
    elif score >= 285:
        return "B2"  # Teto máximo B2 para Listening
    else:
        return None


def format_listening_csa_display(listening_score, obtained_level, points):
    """
    Formata a exibição do Listening CSA para a UI.
    
    Args:
        listening_score (int): Pontuação de listening
        obtained_level (str): Nível CEFR obtido
        points (float): Pontos CSA
    
    Returns:
        str: String formatada para exibição
    """
    if listening_score is None or obtained_level is None:
        return f"Listening: N/A | Listening CSA: {points}/5"
    
    return f"Listening: {listening_score} ({obtained_level}) | Listening CSA: {points}/5"