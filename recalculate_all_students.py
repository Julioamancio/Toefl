#!/usr/bin/env python3
"""
Script para recalcular todos os níveis CEFR dos alunos após mudanças nos critérios
"""

from app import app
from models import db, Student

def recalculate_all_students():
    """Recalcula os níveis CEFR de todos os alunos"""
    with app.app_context():
        print("🔄 Iniciando recálculo de todos os alunos...")
        
        # Buscar todos os alunos
        students = Student.query.all()
        total_students = len(students)
        
        print(f"📊 Total de alunos encontrados: {total_students}")
        
        updated_count = 0
        
        for i, student in enumerate(students, 1):
            try:
                # Recalcular CEFR final baseado na pontuação total
                if student.total is not None:
                    old_cefr = student.cefr_geral
                    new_cefr = student.calculate_final_cefr()
                    student.cefr_geral = new_cefr
                    
                    # Atualizar cálculos do TOEFL (listening, etc.)
                    student.update_toefl_calculations()
                    
                    if old_cefr != new_cefr:
                        print(f"  ✅ {student.name} ({student.student_number}): {old_cefr} → {new_cefr}")
                        updated_count += 1
                    
                    # Progresso a cada 10 alunos
                    if i % 10 == 0:
                        print(f"  📈 Progresso: {i}/{total_students} alunos processados")
                        
            except Exception as e:
                print(f"  ❌ Erro ao processar {student.name}: {e}")
        
        # Salvar todas as mudanças
        try:
            db.session.commit()
            print(f"\n✅ Recálculo concluído!")
            print(f"📊 Total de alunos processados: {total_students}")
            print(f"🔄 Alunos com CEFR atualizado: {updated_count}")
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro ao salvar mudanças: {e}")

if __name__ == "__main__":
    recalculate_all_students()