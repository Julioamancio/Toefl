#!/usr/bin/env python3
"""
Script para recalcular todos os ComputedLevels após correção dos thresholds
"""

from app import app
from models import db, Student, ComputedLevel, calculate_student_levels

def recalculate_computed_levels():
    """Recalcula todos os ComputedLevels com os novos thresholds"""
    with app.app_context():
        print("🔄 Iniciando recálculo de todos os ComputedLevels...")
        
        # Buscar todos os estudantes
        students = Student.query.all()
        total_students = len(students)
        
        print(f"📊 Total de estudantes encontrados: {total_students}")
        
        updated_count = 0
        
        for i, student in enumerate(students, 1):
            try:
                # Buscar ComputedLevel existente
                computed_level = ComputedLevel.query.filter_by(student_id=student.id).first()
                
                # Calcular novos níveis
                levels, applied_rules = calculate_student_levels(student)
                
                if computed_level:
                    # Atualizar existente
                    old_overall = computed_level.overall_level
                    computed_level.school_level = levels.get('school_level')
                    computed_level.listening_level = levels.get('listening_level')
                    computed_level.lfm_level = levels.get('lfm_level')
                    computed_level.reading_level = levels.get('reading_level')
                    computed_level.overall_level = levels.get('overall_level')
                    computed_level.applied_rules = '; '.join(applied_rules)
                    
                    if old_overall != computed_level.overall_level:
                        print(f"  ✅ {student.name} ({student.student_number}): {old_overall} → {computed_level.overall_level}")
                        updated_count += 1
                else:
                    # Criar novo
                    computed_level = ComputedLevel(
                        student_id=student.id,
                        school_level=levels.get('school_level'),
                        listening_level=levels.get('listening_level'),
                        lfm_level=levels.get('lfm_level'),
                        reading_level=levels.get('reading_level'),
                        overall_level=levels.get('overall_level'),
                        applied_rules='; '.join(applied_rules)
                    )
                    db.session.add(computed_level)
                    print(f"  ➕ {student.name} ({student.student_number}): Novo ComputedLevel → {computed_level.overall_level}")
                    updated_count += 1
                
                # Progresso a cada 10 estudantes
                if i % 10 == 0:
                    print(f"  📈 Progresso: {i}/{total_students} estudantes processados")
                    
            except Exception as e:
                print(f"  ❌ Erro ao processar {student.name}: {e}")
        
        # Commit das alterações
        db.session.commit()
        
        print(f"\n✅ Recálculo concluído!")
        print(f"📊 {updated_count} ComputedLevels atualizados/criados")
        
        # Verificar alguns exemplos
        print("\n🔍 Verificando alguns exemplos:")
        examples = Student.query.limit(5).all()
        for student in examples:
            computed = ComputedLevel.query.filter_by(student_id=student.id).first()
            if computed:
                print(f"  • {student.name}: Listening={student.listening} → {computed.listening_level}, Overall={computed.overall_level}")

if __name__ == '__main__':
    recalculate_computed_levels()