#!/usr/bin/env python3
"""
Módulo para calcular relevância da busca com priorização por primeiro nome e número de matches
"""

def calculate_search_relevance(student, search_terms):
    """
    Calcula a relevância de um estudante para os termos de busca
    IMPORTANTE: O primeiro termo de busca DEVE ser encontrado no primeiro nome do estudante
    
    Critérios de pontuação:
    - Primeiro nome: 20 pontos por termo encontrado
    - Último nome: 15 pontos por termo encontrado  
    - Nome do meio: 10 pontos por termo encontrado
    - Qualquer posição: 5 pontos por termo encontrado
    - Número do estudante: 3 pontos por termo encontrado
    
    Args:
        student: Objeto Student
        search_terms: Lista de termos de busca
        
    Returns:
        dict: {
            'score': int,           # Pontuação total
            'matches': int,         # Número de termos encontrados
            'first_name_matches': int,  # Matches no primeiro nome
            'last_name_matches': int,   # Matches no último nome
            'details': list         # Detalhes dos matches
        }
    """
    
    if not student or not student.name or not search_terms:
        return {
            'score': 0,
            'matches': 0,
            'first_name_matches': 0,
            'last_name_matches': 0,
            'details': []
        }
    
    # Parse student name parts
    # IMPORTANTE: No sistema, os nomes estão no formato "Sobrenome Nome [Nomes do meio]"
    name_parts = student.name.strip().split()
    if not name_parts:
        return {
            'score': 0,
            'matches': 0,
            'first_name_matches': 0,
            'last_name_matches': 0,
            'details': []
        }
    
    # Ajustando para o formato real do sistema:
    # - name_parts[0] = Sobrenome (último nome real)
    # - name_parts[1] = Primeiro nome real
    # - name_parts[2:] = Nomes do meio
    surname = name_parts[0].lower() if len(name_parts) > 0 else ""
    first_name = name_parts[1].lower() if len(name_parts) > 1 else ""
    middle_names = [part.lower() for part in name_parts[2:]] if len(name_parts) > 2 else []
    full_name_lower = student.name.lower()
    student_number_lower = (student.student_number or "").lower()
    
    # REGRA OBRIGATÓRIA: O primeiro termo DEVE estar no primeiro nome REAL (segunda posição)
    if search_terms:
        first_term = search_terms[0].lower().strip()
        if first_term and first_name:
            # Verifica se o primeiro termo está no primeiro nome real
            if not (first_name.startswith(first_term) or first_term in first_name):
                # Se o primeiro termo não está no primeiro nome real, retorna score 0
                return {
                    'score': 0,
                    'matches': 0,
                    'first_name_matches': 0,
                    'last_name_matches': 0,
                    'details': []
                }
    
    total_score = 0
    matches_found = 0
    first_name_matches = 0
    last_name_matches = 0
    details = []
    
    for term in search_terms:
        term_lower = term.lower().strip()
        if not term_lower:
            continue
            
        term_score = 0
        term_matches = []
        
        # 1. Primeiro nome REAL (prioridade máxima) - segunda posição no array
        if first_name and first_name.startswith(term_lower):
            term_score += 20
            term_matches.append(f"primeiro nome: '{first_name}'")
            first_name_matches += 1
        elif first_name and term_lower in first_name:
            term_score += 15
            term_matches.append(f"primeiro nome (parcial): '{first_name}'")
            first_name_matches += 1
        
        # 2. Sobrenome (segunda prioridade) - primeira posição no array
        elif surname and surname.startswith(term_lower):
            term_score += 15
            term_matches.append(f"sobrenome: '{surname}'")
            last_name_matches += 1
        elif surname and term_lower in surname:
            term_score += 12
            term_matches.append(f"sobrenome (parcial): '{surname}'")
            last_name_matches += 1
        
        # 3. Nomes do meio
        else:
            middle_match = False
            for middle in middle_names:
                if middle.startswith(term_lower):
                    term_score += 10
                    term_matches.append(f"nome do meio: '{middle}'")
                    middle_match = True
                    break
                elif term_lower in middle:
                    term_score += 8
                    term_matches.append(f"nome do meio (parcial): '{middle}'")
                    middle_match = True
                    break
            
            # 4. Qualquer posição no nome (se não encontrou em posições específicas)
            if not middle_match and term_lower in full_name_lower:
                term_score += 5
                term_matches.append(f"qualquer posição no nome")
        
        # 5. Número do estudante
        if term_lower in student_number_lower:
            term_score += 3
            term_matches.append(f"número do estudante: '{student.student_number}'")
        
        # Se encontrou o termo em algum lugar
        if term_score > 0:
            matches_found += 1
            total_score += term_score
            details.append({
                'term': term,
                'score': term_score,
                'matches': term_matches
            })
    
    return {
        'score': total_score,
        'matches': matches_found,
        'first_name_matches': first_name_matches,
        'last_name_matches': last_name_matches,
        'details': details
    }

def sort_students_by_relevance(students, search_terms):
    """
    Ordena estudantes por relevância da busca
    
    Critérios de ordenação (em ordem de prioridade):
    1. Número de termos encontrados (mais matches primeiro)
    2. Número de matches no primeiro nome (prioridade)
    3. Pontuação total de relevância
    4. Nome alfabético (desempate)
    
    Args:
        students: Lista de objetos Student
        search_terms: Lista de termos de busca
        
    Returns:
        list: Lista de tuplas (student, relevance_data) ordenada por relevância
    """
    
    if not students or not search_terms:
        return [(student, None) for student in students]
    
    # Calcula relevância para cada estudante
    students_with_relevance = []
    for student in students:
        relevance = calculate_search_relevance(student, search_terms)
        students_with_relevance.append((student, relevance))
    
    # Ordena por critérios de relevância
    def sort_key(item):
        student, relevance = item
        if not relevance:
            return (0, 0, 0, student.name or "")
        
        return (
            -relevance['matches'],           # Mais matches primeiro (negativo para desc)
            -relevance['first_name_matches'], # Mais matches no primeiro nome primeiro
            -relevance['score'],            # Maior pontuação primeiro
            student.name or ""              # Nome alfabético para desempate
        )
    
    return sorted(students_with_relevance, key=sort_key)

def format_relevance_debug(student, relevance_data, search_terms):
    """
    Formata informações de relevância para debug
    
    Args:
        student: Objeto Student
        relevance_data: Dados de relevância
        search_terms: Termos de busca
        
    Returns:
        str: String formatada com informações de debug
    """
    
    if not relevance_data:
        return f"{student.name}: Sem dados de relevância"
    
    lines = [
        f"👤 {student.name} (#{student.student_number})",
        f"   📊 Pontuação: {relevance_data['score']} | Matches: {relevance_data['matches']}/{len(search_terms)}",
        f"   🎯 Primeiro nome: {relevance_data['first_name_matches']} | Último nome: {relevance_data['last_name_matches']}"
    ]
    
    if relevance_data['details']:
        lines.append("   📝 Detalhes:")
        for detail in relevance_data['details']:
            matches_str = ", ".join(detail['matches'])
            lines.append(f"      • '{detail['term']}' ({detail['score']}pts): {matches_str}")
    
    return "\n".join(lines)