"""
Cálculo de Listening CSA (escala 0–5) baseado EXCLUSIVAMENTE em listening score (200–300)
e na identificação automática do grupo (6º ano, 9.1, 9.2/9.3) por turma/nivel.

Regras:
- 6º ano (FUND-6*, nivel 6.*):
  - Faixa máxima: A2 (200–245)
  - 200 = 3.0 | 245 = 5.0
  - Fora da faixa → limitar entre 3.0–5.0
  - nota = 3.0 + ((listening - 200) / (245 - 200)) * (5.0 - 3.0)
- 9.1 (FUND-9*, nivel 9.1):
  - Faixa máxima: B1 (200–275)
  - 200 = 3.0 | 275 = 5.0
  - Fora da faixa → limitar entre 3.0–5.0
  - nota = 3.0 + ((listening - 200) / (275 - 200)) * (5.0 - 3.0)
- 9.2/9.3 (FUND-9*, nivel 9.2/9.3 ou nivel vazio):
  - Usa o cálculo normal CEFR (A2→B2):
  - 200–245 = 0→2 | 246–275 = 2→3.5 | 276–300 = 3.5→5.0

Saída é limitada a 0.00–5.00 com duas casas decimais.
"""

def _clamp_and_round(points: float) -> float:
    """Limita a 0–5 e arredonda para duas casas."""
    points = max(0.0, min(5.0, points))
    return round(points + 1e-9, 2)

def _csa_6th(listening_score: int) -> float:
    """Regra 6º ano: 200-245 = 3.0-5.0"""
    if listening_score is None:
        return 3.0
    if listening_score < 200:
        return 3.0
    if listening_score <= 245:
        return 3.0 + ((listening_score - 200) / (245 - 200)) * (5.0 - 3.0)
    return 5.0

def _csa_9_1(listening_score: int) -> float:
    """Regra 9.1: 200-275 = 2.0-5.0"""
    if listening_score is None:
        return 2.0
    if listening_score < 200:
        return 2.0
    if listening_score <= 275:
        return 2.0 + ((listening_score - 200) / (275 - 200)) * (5.0 - 2.0)
    return 5.0

def _csa_9_23(listening_score: int) -> float:
    """Regra 9.2/9.3: Cálculo CEFR normal (A2→B2)"""
    if listening_score is None:
        return 0.0
    if listening_score < 200:
        return 0.0
    if listening_score <= 245:  # A2: 200-245 = 0-2
        return ((listening_score - 200) / (245 - 200)) * 2.0
    elif listening_score <= 275:  # B1: 246-275 = 2-3.5
        return 2.0 + ((listening_score - 246) / (275 - 246)) * 1.5
    else:  # B2: 276-300 = 3.5-5.0
        return 3.5 + ((listening_score - 276) / (300 - 276)) * 1.5

def compute_listening_csa(rotulo_escolar, listening_score, turma_name=None):
    """
    Calcula os pontos de Listening CSA conforme regras atuais.
    - Identifica grupo por `turma_name` (prefixo FUND-6/FUND-9) e/ou `rotulo_escolar` (6.*, 9.1, 9.2, 9.3).
    - Usa `listening_score` (200–300). Retorna dict com chave 'points'.
    """
    if listening_score is None:
        return {'points': 0.0, 'expected_level': None, 'obtained_level': None, 'adjustment': 0}

    rotulo = (str(rotulo_escolar).strip() if rotulo_escolar is not None else '')
    turma_upper = (str(turma_name).strip().upper() if turma_name else '')

    # Determinação do grupo
    group = None
    if turma_upper.startswith('FUND-6') or rotulo.startswith('6'):
        group = '6'
    elif turma_upper.startswith('FUND-9'):
        if rotulo == '9.1':
            group = '9.1'
        else:
            # 9.2/9.3 ou vazio → tratar como 9.2/9.3
            group = '9.23'
    else:
        # Sem turma ou turma diferente: inferir pelo rótulo
        if rotulo == '9.1':
            group = '9.1'
        elif rotulo in ('9.2', '9.3'):
            group = '9.23'
        elif rotulo.startswith('6'):
            group = '6'

    # Cálculo por grupo
    if group == '6':
        pts = _csa_6th(listening_score)
        expected = '6º ano'
    elif group == '9.1':
        pts = _csa_9_1(listening_score)
        expected = '9.1'
    else:
        pts = _csa_9_23(listening_score)
        expected = '9.2/9.3'

    return {
        'points': _clamp_and_round(pts),
        'expected_level': expected,
        'obtained_level': None,
        'adjustment': 0
    }