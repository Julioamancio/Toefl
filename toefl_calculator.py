"""
Funções de cálculo para o sistema TOEFL Junior
Implementa classificação CEFR, rótulos escolares e cálculo proporcional de notas
"""

from toefl_config import (
    CEFR_LISTENING_RANGES, SCHOOL_LABELS, SUBFAIXAS, 
    FLOORS_CAPS, GRADE_CONFIG, SCHOOL_LABEL_ORDER
)

def cefr_listening(score):
    """
    Classifica uma pontuação de Listening (200-300) em nível CEFR
    
    Args:
        score (int/float): Pontuação de Listening (200-300)
        
    Returns:
        str: Nível CEFR ('A1 Starter', 'A1', 'A2', 'A2+', 'B1', 'B2')
    """
    if score is None or score < 200:
        return 'A1 Starter'
    
    score = float(score)
    
    # Classificação corrigida para coerência com school_label
    if 200 <= score <= 245:        # A2 (6º ano nível 2)
        return 'A2'
    elif 246 <= score <= 265:      # A2+ (transição)
        return 'A2+'
    elif 266 <= score <= 285:      # B1 (6º ano nível 3)
        return 'B1'
    elif 286 <= score <= 300:      # B2 (9º ano)
        return 'B2'
    elif score >= 301:             # B2+ (acima do máximo)
        return 'B2+'
    else:                          # < 200 (A1)
        return 'A1'

def school_label(score):
    """
    Converte uma pontuação de Listening em rótulo escolar
    
    Args:
        score (int/float): Pontuação de Listening (200-300+)
        
    Returns:
        str: Rótulo escolar ('6.1', '6.2', '6.3', '9.1', '9.2', '9.3')
    """
    if score is None or score < 200:
        return '6.1'
    
    score = float(score)
    
    # Regras de classificação corrigidas para coerência
    if 200 <= score <= 245:        # A2 (6º ano nível 2)
        return '6.2'
    elif 246 <= score <= 285:      # A2+ (6º ano nível 3)
        return '6.3'
    elif 286 <= score <= 299:      # B1 (9º ano nível 1)
        return '9.1'
    elif 300 <= score <= 310:      # B2 (9º ano nível 2)
        return '9.2'
    elif score >= 311:             # B2+ (9º ano nível 3)
        return '9.3'
    else:                          # < 200 (A1 - 6º ano nível 1)
        return '6.1'

def get_subfaixa_key(score, label_aluno):
    """
    Determina a chave da subfaixa para cálculo proporcional
    
    Args:
        score (float): Pontuação do aluno
        label_aluno (str): Rótulo escolar do aluno
        
    Returns:
        str: Chave da subfaixa ('6.1', '6.2', '6.3_A2', '6.3_A2+', '9.1', '9.2')
    """
    if label_aluno == '6.3':
        # Para 6.3, precisa distinguir entre A2 (246-265) e A2+ (266-285)
        if 246 <= score <= 265:
            return '6.3_A2'
        elif 266 <= score <= 285:
            return '6.3_A2+'
        else:
            return '6.3_A2'  # fallback
    else:
        return label_aluno

def calculate_proportional_position(score, subfaixa_key):
    """
    Calcula a posição proporcional dentro da subfaixa (0.0 a 1.0)
    
    Args:
        score (float): Pontuação do aluno
        subfaixa_key (str): Chave da subfaixa
        
    Returns:
        float: Posição proporcional (0.0 a 1.0)
    """
    if subfaixa_key not in SUBFAIXAS:
        return 1.0
    
    subfaixa = SUBFAIXAS[subfaixa_key]
    min_score = subfaixa['min']
    max_score = subfaixa['max']
    
    if subfaixa_key in ['9.2', '9.3']:  # B2 e B2+ são valores máximos
        return 1.0
    
    if max_score == min_score:  # Evita divisão por zero
        return 1.0
    
    # Cálculo proporcional: p = (S - min) / (max - min)
    p = (score - min_score) / (max_score - min_score)
    
    # Garante que p está entre 0.0 e 1.0
    return max(0.0, min(1.0, p))

def get_label_index(label):
    """
    Retorna o índice hierárquico de um rótulo escolar
    
    Args:
        label (str): Rótulo escolar
        
    Returns:
        int: Índice na hierarquia (menor = mais baixo)
    """
    try:
        return SCHOOL_LABEL_ORDER.index(label)
    except ValueError:
        return 0  # fallback para o menor nível

def grade_listening(score, meta_label, max_points=5.0):
    """
    Calcula a nota de Listening (0-5) com base na pontuação e meta da turma
    Usa a função compute_listening_csa atualizada
    
    Args:
        score (int/float): Pontuação de Listening (200-300)
        meta_label (str): Meta da turma ('6.1', '6.2', '6.3', '9.1', '9.2', '9.3')
        max_points (float): Pontuação máxima (padrão: 5.0)
        
    Returns:
        float: Nota calculada (0.0 a 5.0), arredondada em 1 casa decimal
    """
    if score is None:
        return 0.0
    
    # Validação da meta_label
    if meta_label is None or meta_label == '':
        return 0.0
    
    try:
        # Importar a função de cálculo atualizada
        from listening_csa import compute_listening_csa
        
        # Converter meta_label para float se necessário
        if isinstance(meta_label, str):
            rotulo_escolar = float(meta_label)
        else:
            rotulo_escolar = meta_label
        
        return compute_listening_csa(rotulo_escolar, score)
    except (ValueError, TypeError, ImportError):
        # Fallback para lógica simples se houver erro
        score = float(score)
        return round(min(score / 300 * max_points, max_points), 1)

def get_student_classification(score):
    """
    Retorna classificação completa do estudante
    
    Args:
        score (int/float): Pontuação de Listening
        
    Returns:
        dict: Dicionário com classificação completa
    """
    if score is None:
        return {
            'score': None,
            'cefr': 'A1 Starter',
            'school_label': '6.1',
            'subfaixa': '6.1'
        }
    
    score = float(score)
    cefr = cefr_listening(score)
    label = school_label(score)
    subfaixa = get_subfaixa_key(score, label)
    
    return {
        'score': score,
        'cefr': cefr,
        'school_label': label,
        'subfaixa': subfaixa
    }

def validate_score(score):
    """
    Valida se uma pontuação está no range válido do TOEFL Junior
    
    Args:
        score: Pontuação a ser validada
        
    Returns:
        tuple: (is_valid, normalized_score, error_message)
    """
    if score is None:
        return False, None, "Pontuação não pode ser nula"
    
    try:
        score = float(score)
    except (ValueError, TypeError):
        return False, None, "Pontuação deve ser um número"
    
    if score < 200:
        return False, None, "Pontuação mínima é 200"
    
    if score > 350:
        # Permite scores > 350 mas trata como 350 (limite superior expandido)
        return True, 350.0, f"Pontuação {score} tratada como 350 (teto expandido do teste)"
    
    return True, score, None