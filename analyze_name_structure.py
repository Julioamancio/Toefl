from app import app
from models import Student

with app.app_context():
    print('🔍 ANÁLISE DA ESTRUTURA DOS NOMES NO BANCO DE DADOS')
    print('=' * 60)
    
    # Buscar alguns exemplos de nomes
    students = Student.query.limit(20).all()
    
    print('\n📋 Exemplos de nomes no sistema:')
    for i, student in enumerate(students, 1):
        name_parts = student.name.split()
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[-1] if len(name_parts) > 1 else ""
        middle_names = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else ""
        
        print(f'{i:2d}. {student.name}')
        print(f'    Primeiro: "{first_name}" | Último: "{last_name}" | Meio: "{middle_names}"')
    
    print('\n🔍 Analisando casos específicos:')
    
    # Procurar por "Lago Diego"
    lago_diego = Student.query.filter(Student.name.ilike('%Lago%')).filter(Student.name.ilike('%Diego%')).first()
    if lago_diego:
        parts = lago_diego.name.split()
        print(f'\n✅ Encontrado: {lago_diego.name}')
        print(f'   Primeiro nome: "{parts[0]}"')
        print(f'   Último nome: "{parts[-1]}"')
        print(f'   Estrutura: {parts}')
    
    # Procurar por nomes com "Diego"
    diego_students = Student.query.filter(Student.name.ilike('%Diego%')).all()
    print(f'\n📊 Estudantes com "Diego": {len(diego_students)}')
    for student in diego_students:
        parts = student.name.split()
        diego_position = None
        for i, part in enumerate(parts):
            if 'diego' in part.lower():
                diego_position = i
                break
        
        print(f'   • {student.name}')
        print(f'     "Diego" está na posição {diego_position} (0=primeiro, {len(parts)-1}=último)')
    
    print('\n🎯 CONCLUSÕES:')
    print('   • No nosso sistema: "Lago Diego" - Diego é o ÚLTIMO nome')
    print('   • Na planilha: "DIEGO MOTTA LAGO" - Diego é o PRIMEIRO nome')
    print('   • Precisamos buscar por primeiro nome E último nome')
    
    print('\n💡 ESTRATÉGIA DE BUSCA PROPOSTA:')
    print('   1. Dividir a busca em termos')
    print('   2. Para cada termo, verificar se é primeiro OU último nome')
    print('   3. Priorizar matches de primeiro nome')
    print('   4. Depois verificar último nome')
    print('   5. Por último, verificar nomes do meio')