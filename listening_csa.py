"""
Cálculo de Listening CSA (escala 0–5) baseado EXCLUSIVAMENTE em score_total (600–900)
e na identificação automática do grupo (6º ano, 9.1, 9.2/9.3) por turma/nivel.

Regras:
- 6º ano (FUND-6*, nivel 6.*):
  - total < 600 → 3.00
  - 600–649 → linear 3.00 → 5.00
  - > 649 → 5.00
- 9.1 (FUND-9*, nivel 9.1):
  - total < 600 → 0.00
  - 600–864 → linear 0.00 → 5.00
  - > 864 → 5.00
- 9.2/9.3 (FUND-9*, nivel 9.2/9.3 ou nivel vazio):
  - total < 600 → 0.00
  - 600–900 → linear 0.00 → 5.00

Saída é limitada a 0.00–5.00 com duas casas decimais.
"""

def _clamp_and_round(points: float) -> float:
    """Limita a 0–5 e arredonda para duas casas."""
    points = max(0.0, min(5.0, points))
    return round(points + 1e-9, 2)

def _csa_6th(total: int) -> float:
    if total is None:
        return 0.0
    if total < 600:
        return 3.0
    if total <= 649:
        return 3.0 + ((total - 600) / (649 - 600)) * (5.0 - 3.0)
    return 5.0

def _csa_9_1(total: int) -> float:
    if total is None or total < 600:
        return 0.0
    if total <= 864:
        return ((total - 600) / (864 - 600)) * 5.0
    return 5.0

def _csa_9_23(total: int) -> float:
    if total is None or total < 600:
        return 0.0
    return ((total - 600) / (900 - 600)) * 5.0

def compute_listening_csa(rotulo_escolar, score_total, turma_name=None):
    """
    Calcula os pontos de Listening CSA conforme regras atuais.
    - Identifica grupo por `turma_name` (prefixo FUND-6/FUND-9) e/ou `rotulo_escolar` (6.*, 9.1, 9.2, 9.3).
    - Usa `score_total` (600–900). Retorna dict com chave 'points'.
    """
    if score_total is None:
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
        pts = _csa_6th(score_total)
        expected = '6º ano'
    elif group == '9.1':
        pts = _csa_9_1(score_total)
        expected = '9.1'
    else:
        pts = _csa_9_23(score_total)
        expected = '9.2/9.3'

    return {
        'points': _clamp_and_round(pts),
        'expected_level': expected,
        'obtained_level': None,
        'adjustment': 0
    }