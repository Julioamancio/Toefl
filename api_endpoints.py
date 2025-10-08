"""
API endpoints para retornar dados de estudantes com pontuações e rótulos separadamente
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required
from models import db, Student, ComputedLevel, Class, Teacher

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/students')
@login_required
def get_students():
    """
    Retorna lista de estudantes com pontuações e rótulos separados
    
    Returns:
        JSON com dados dos estudantes incluindo:
        - listening_score, listening_label
        - lfm_score, lfm_label  
        - reading_score, reading_label
        - overall_level (corrigido)
        - cefr_geral_raw (apenas para referência)
    """
    # Aplicar filtros se fornecidos
    search = request.args.get('search', '')
    class_filter = request.args.get('class_filter', 0, type=int)
    cefr_filter = request.args.get('cefr_filter', '')
    class_name = request.args.get('class_name', '')
    sheet_name = request.args.get('sheet_name', '')
    teacher = request.args.get('teacher', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Query base
    query = Student.query.join(ComputedLevel, Student.id == ComputedLevel.student_id, isouter=True)
    
    # Aplicar filtros
    if search:
        # Busca inteligente com múltiplos nomes
        # Suporta separação por vírgula, quebra de linha ou ponto e vírgula
        search_lines = []
        
        # Primeiro, divide por quebras de linha
        for line in search.strip().split('\n'):
            line = line.strip()
            if line:
                # Depois divide por vírgula ou ponto e vírgula
                if ',' in line:
                    search_lines.extend([name.strip() for name in line.split(',') if name.strip()])
                elif ';' in line:
                    search_lines.extend([name.strip() for name in line.split(';') if name.strip()])
                else:
                    search_lines.append(line)
        
        # Se não há separadores, trata como busca normal
        if not search_lines:
            search_lines = [search.strip()]
        
        # Para cada nome na lista, cria condições de busca
        all_conditions = []
        
        for search_name in search_lines:
            if not search_name:
                continue
                
            # Divide cada nome em termos
            search_terms = search_name.strip().split()
            
            if len(search_terms) == 1:
                # Busca simples com um termo - considerando estrutura "Sobrenome Nome"
                term = search_terms[0]
                
                # Para nomes no formato "Sobrenome Nome", precisamos ser mais específicos
                # Vamos usar apenas condições que realmente fazem sentido para a estrutura de nomes
                name_conditions = [
                    # APENAS primeiro nome (segunda posição): "Sobrenome TERMO"
                    Student.name.ilike(f'% {term}'),    # Termina com o termo (primeiro nome)
                ]
                
                # Condição para número do estudante (mantida para casos especiais)
                number_condition = Student.student_number.ilike(f'%{term}%')
                
                # Combina: APENAS primeiro nome OU número
                all_conditions.append(db.or_(*name_conditions, number_condition))
            else:
                # Busca com múltiplos termos - busca inteligente por posição
                search_conditions = []
                
                # Para cada termo, verifica se pode ser primeiro ou último nome
                for i, term in enumerate(search_terms):
                    term_conditions = []
                    
                    if i == 0:  # Primeiro termo da busca
                        # APENAS primeiro nome (segunda posição) - regra restritiva
                        term_conditions.extend([
                            Student.name.ilike(f'% {term}'),  # Primeiro nome (segunda posição)
                        ])
                    elif i == len(search_terms) - 1:  # Último termo da busca
                        # APENAS primeiro nome (segunda posição) - regra restritiva
                        term_conditions.extend([
                            Student.name.ilike(f'% {term}'),  # Primeiro nome (segunda posição)
                        ])
                    else:  # Termos do meio
                        # APENAS primeiro nome (segunda posição) - regra restritiva
                        term_conditions.append(Student.name.ilike(f'% {term}'))
                    
                    # Cada termo deve ser encontrado (AND entre termos)
                    search_conditions.append(db.or_(*term_conditions))
                
                # TODOS os termos devem ser encontrados (busca exata)
                name_and_condition = db.and_(*search_conditions)
                
                # Também permite busca no número do estudante
                number_condition = Student.student_number.ilike(f'%{search_name}%')
                
                # Combina: (busca inteligente no nome) OU (nome completo no número)
                exact_condition = db.or_(name_and_condition, number_condition)
                
                # Se a busca exata não encontrar resultados, tenta busca flexível
                # Primeiro testa se a busca exata retorna algo
                exact_results = Student.query.filter(exact_condition).all()
                
                if exact_results:
                    # Se encontrou com busca exata, usa ela
                    all_conditions.append(exact_condition)
                else:
                    # Se não encontrou, usa busca flexível RESTRITIVA (apenas primeiro nome)
                    flexible_conditions = []
                    for term in search_terms:
                        term_flexible = [
                            # APENAS primeiro nome (segunda posição) - regra restritiva
                            Student.name.ilike(f'% {term}'),  # Primeiro nome
                            Student.student_number.ilike(f'%{term}%')  # Número
                        ]
                        flexible_conditions.append(db.or_(*term_flexible))
                    
                    # Na busca flexível, pelo menos UM termo deve ser encontrado
                    all_conditions.append(db.or_(*flexible_conditions))
        
        # Combina todas as condições de todos os nomes com OR
        if all_conditions:
            query = query.filter(db.or_(*all_conditions))
    
    if class_filter:
        query = query.filter(Student.class_id == class_filter)

    if cefr_filter:
        query = query.filter(ComputedLevel.overall_level == cefr_filter)

    if class_name:
        query = query.join(Class, Student.class_id == Class.id, isouter=True)
        query = query.filter(Class.name.ilike(f'%{class_name}%'))

    if sheet_name:
        query = query.filter(Student.import_sheet_name.ilike(f'%{sheet_name}%'))

    if teacher:
        query = query.join(Teacher, Student.teacher_id == Teacher.id, isouter=True)
        query = query.filter(Teacher.name.ilike(f'%{teacher}%'))
    
    # Se há busca ativa, aplica ordenação por relevância
    if search and all_conditions:
        # Importa módulo de relevância
        from search_relevance import sort_students_by_relevance
        
        # Coleta todos os termos de busca de todas as linhas
        all_search_terms = []
        for search_name in search_lines:
            if search_name:
                all_search_terms.extend(search_name.strip().split())
        
        # Remove duplicatas mantendo ordem
        unique_terms = []
        for term in all_search_terms:
            if term not in unique_terms:
                unique_terms.append(term)
        
        # Aplica ordenação por relevância antes da paginação
        all_students = query.all()
        students_with_relevance = sort_students_by_relevance(all_students, unique_terms)
        
        # Extrai apenas os estudantes ordenados por relevância
        ordered_students = [student for student, relevance in students_with_relevance]
        
        # Aplica paginação manual nos resultados ordenados
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_students = ordered_students[start_idx:end_idx]
        
        # Cria objeto de paginação manual
        class ManualPagination:
            def __init__(self, items, page, per_page, total):
                self.items = items
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = (total + per_page - 1) // per_page
                self.has_next = page < self.pages
                self.has_prev = page > 1
        
        students = ManualPagination(paginated_students, page, per_page, len(ordered_students))
    else:
        # Paginação normal quando não há busca
        students = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
    
    # Preparar dados de resposta
    student_data = []
    for student in students.items:
        computed_level = ComputedLevel.query.filter_by(student_id=student.id).first()
        
        # Calcular Listening CSA
        from listening_csa import compute_listening_csa
        listening_csa_data = None
        if student.class_info and student.class_info.meta_label and student.listening:
            try:
                listening_csa_data = compute_listening_csa(student.class_info.meta_label, student.listening)
            except (ValueError, TypeError):
                listening_csa_data = None
        
        data = {
            'id': student.id,
            'name': student.name,
            'student_number': student.student_number,
            'class_id': student.class_id,
            
            # Listening
            'listening': student.listening,
            'listening_label': student.list_cefr or 'N/A',
            
            # LFM
            'lfm': student.lfm,
            'lfm_label': student.lfm_cefr or 'N/A',
            
            # Reading
            'reading': student.reading,
            'reading_label': student.read_cefr or 'N/A',
            
            # Total
            'total': student.total,
            
            # Níveis
            'overall_level': computed_level.overall_level if computed_level else 'N/A',
            'cefr_geral_raw': student.cefr_geral,  # Para referência apenas
            
            # Listening CSA
            'listening_csa_points': student.listening_csa_points,
            'expected_level': listening_csa_data['expected_level'] if listening_csa_data else None,
            'obtained_level': listening_csa_data['obtained_level'] if listening_csa_data else None,
            
            # Outros dados
            'lexile': student.lexile,
            'class_name': student.class_info.name if student.class_info else None,
            'teacher_name': student.teacher.name if student.teacher else None,
            'import_sheet_name': student.import_sheet_name,
            'turma_meta': student.turma_meta
        }
        
        student_data.append(data)
    
    return jsonify({
        'success': True,
        'students': student_data,
        'pagination': {
            'page': students.page,
            'pages': students.pages,
            'per_page': students.per_page,
            'total': students.total,
            'has_next': students.has_next,
            'has_prev': students.has_prev
        }
    })

@api_bp.route('/students/<int:student_id>')
@login_required
def get_student_detail(student_id):
    """
    Retorna detalhes de um estudante específico com cálculo aplicado e guardrails
    """
    student = Student.query.get_or_404(student_id)
    computed_level = ComputedLevel.query.filter_by(student_id=student.id).first()
    
    # Calcular níveis e regras aplicadas
    from models import calculate_student_levels
    levels, applied_rules = calculate_student_levels(student)
    
    # Calcular Listening CSA
    from listening_csa import compute_listening_csa
    listening_csa_data = None
    if student.class_info and student.class_info.meta_label and student.listening:
        try:
            listening_csa_data = compute_listening_csa(student.class_info.meta_label, student.listening)
        except (ValueError, TypeError):
            listening_csa_data = None
    
    data = {
        'id': student.id,
        'name': student.name,
        'student_number': student.student_number,
        'class_id': student.class_id,
        
        # Pontuações e rótulos
        'listening': student.listening,
        'listening_label': student.list_cefr or 'N/A',
        'lfm': student.lfm,
        'lfm_label': student.lfm_cefr or 'N/A',
        'reading': student.reading,
        'reading_label': student.read_cefr or 'N/A',
        'total': student.total,
        
        # Níveis calculados
        'calculated_levels': levels,
        'overall_level': computed_level.overall_level if computed_level else levels.get('overall_level', 'N/A'),
        'cefr_geral_raw': student.cefr_geral,
        
        # Listening CSA
        'listening_csa_points': student.listening_csa_points,
        'expected_level': listening_csa_data['expected_level'] if listening_csa_data else None,
        'obtained_level': listening_csa_data['obtained_level'] if listening_csa_data else None,
        
        # Regras aplicadas
        'applied_rules': applied_rules,
        
        # Outros dados
        'lexile': student.lexile,
        'class_name': student.class_info.name if student.class_info else None,
        'teacher_name': student.teacher.name if student.teacher else None,
        'import_sheet_name': student.import_sheet_name,
        'turma_meta': student.turma_meta
    }
    
    return jsonify({
        'success': True,
        'student': data
    })

@api_bp.route('/dashboard/stats')
@login_required
def get_dashboard_stats():
    """
    Retorna estatísticas do dashboard usando overall_level corrigido
    """
    # Estatísticas gerais
    total_students = Student.query.count()
    total_classes = Class.query.count()
    
    # Distribuição por nível CEFR usando ComputedLevel
    cefr_distribution = db.session.query(
        ComputedLevel.overall_level,
        db.func.count(ComputedLevel.id)
    ).group_by(ComputedLevel.overall_level).all()
    
    # Calcular nível predominante
    predominant_level = 'N/A'
    if cefr_distribution:
        max_count = max(cefr_distribution, key=lambda x: x[1])
        predominant_level = max_count[0] if max_count[0] else 'N/A'
    
    # Médias por habilidade
    avg_scores = db.session.query(
        db.func.avg(Student.listening),
        db.func.avg(Student.reading),
        db.func.avg(Student.lfm),
        db.func.avg(Student.total)
    ).first()
    
    return jsonify({
        'success': True,
        'stats': {
            'total_students': total_students,
            'total_classes': total_classes,
            'predominant_level': predominant_level,
            'cefr_distribution': [{'level': level, 'count': count} for level, count in cefr_distribution],
            'avg_scores': {
                'listening': round(avg_scores[0], 1) if avg_scores[0] else None,
                'reading': round(avg_scores[1], 1) if avg_scores[1] else None,
                'lfm': round(avg_scores[2], 1) if avg_scores[2] else None,
                'total': round(avg_scores[3], 1) if avg_scores[3] else None
            }
        }
    })