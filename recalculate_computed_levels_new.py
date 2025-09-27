#!/usr/bin/env python3
"""
Script para recalcular todos os níveis CEFR dos alunos usando o sistema ComputedLevel
"""

from app import app
from models import db, Student, ComputedLevel, calculate_student_levels

def recalculate_computed_levels():
    """Recalcula os níveis CEFR de todos os alunos usando ComputedLevel"""
    with app.app_context():
        print("🔄 Iniciando recálculo de todos os níveis computados...")
        
        # Buscar todos os alunos
        students = Student.query.all()
        total_students = len(students)
        
        print(f"📊 Total de alunos encontrados: {total_students}")
        
        updated_count = 0
        created_count = 0
        
        for i, student in enumerate(students, 1):
            try:
                # Calcular níveis usando a nova função
                levels, applied_rules = calculate_student_levels(student)
                
                # Buscar ou criar ComputedLevel
                computed_level = ComputedLevel.query.filter_by(student_id=student.id).first()
                
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
                    print(f"  🆕 {student.name} ({student.student_number}): Novo → {computed_level.overall_level}")
                    created_count += 1
                
                # Progresso a cada 50 alunos
                if i % 50 == 0:
                    print(f"  📈 Progresso: {i}/{total_students} alunos processados")
                    db.session.commit()  # Commit parcial
                        
            except Exception as e:
                print(f"  ❌ Erro ao processar {student.name}: {e}")
                continue
        
        # Commit final
        try:
            db.session.commit()
            print("\n✅ Recálculo concluído!")
            print(f"📊 Total de alunos processados: {total_students}")
            print(f"🔄 Níveis atualizados: {updated_count}")
            print(f"🆕 Níveis criados: {created_count}")
        except Exception as e:
            print(f"❌ Erro ao salvar no banco: {e}")
            db.session.rollback()

if __name__ == "__main__":
    recalculate_computed_levels()