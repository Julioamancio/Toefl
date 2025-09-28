from app import create_app
from models import ComputedLevel, Student, db

app, csrf = create_app()

with app.app_context():
    # Verificar dados na tabela ComputedLevel
    levels = ComputedLevel.query.all()
    print(f'Total de registros na ComputedLevel: {len(levels)}')
    
    # Mostrar alguns exemplos
    print("\nPrimeiros 10 registros:")
    for level in levels[:10]:
        print(f'Student ID: {level.student_id}, Overall Level: {level.overall_level}')
    
    # Contar por nível
    print("\nContagem por nível CEFR:")
    level_counts = {}
    for level in levels:
        if level.overall_level:
            level_counts[level.overall_level] = level_counts.get(level.overall_level, 0) + 1
    
    for level_name, count in sorted(level_counts.items()):
        print(f'{level_name}: {count} estudantes')
    
    # Verificar se há estudantes sem ComputedLevel
    students_without_computed = Student.query.outerjoin(ComputedLevel).filter(ComputedLevel.id == None).count()
    print(f'\nEstudantes sem ComputedLevel: {students_without_computed}')