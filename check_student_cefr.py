from app import create_app
from models import Student, ComputedLevel, db

app, csrf = create_app()

with app.app_context():
    # Verificar dados no campo cefr_geral dos estudantes
    students = Student.query.all()
    print(f'Total de estudantes: {len(students)}')
    
    # Contar por nível CEFR no campo cefr_geral
    print("\nContagem por nível CEFR (campo cefr_geral):")
    cefr_counts = {}
    for student in students:
        if student.cefr_geral:
            level = student.cefr_geral.strip()
            cefr_counts[level] = cefr_counts.get(level, 0) + 1
    
    for level_name, count in sorted(cefr_counts.items()):
        print(f'{level_name}: {count} estudantes')
    
    # Comparar com ComputedLevel
    print("\n--- COMPARAÇÃO ---")
    print("Estudantes com B2 no cefr_geral:", Student.query.filter(db.func.trim(Student.cefr_geral) == 'B2').count())
    print("Estudantes com B2 no ComputedLevel:", ComputedLevel.query.filter(ComputedLevel.overall_level == 'B2').count())
    
    # Mostrar alguns exemplos de discrepância
    print("\nPrimeiros 5 estudantes com diferenças:")
    count = 0
    for student in students[:50]:  # Verificar apenas os primeiros 50
        computed = ComputedLevel.query.filter_by(student_id=student.id).first()
        if computed and student.cefr_geral:
            student_level = student.cefr_geral.strip()
            computed_level = computed.overall_level
            if student_level != computed_level:
                print(f"ID {student.id}: cefr_geral='{student_level}' vs ComputedLevel='{computed_level}'")
                count += 1
                if count >= 5:
                    break