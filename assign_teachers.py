#!/usr/bin/env python3
"""
Script para associar professores aos alunos existentes
"""

from app import app, db, Student, Teacher
import random

def assign_teachers_to_students():
    """Associa professores aos alunos de forma aleatória"""
    
    with app.app_context():
        # Buscar todos os professores
        teachers = Teacher.query.all()
        
        if not teachers:
            print("❌ Nenhum professor encontrado!")
            return
        
        print(f"📚 Professores disponíveis: {len(teachers)}")
        for teacher in teachers:
            print(f"   - {teacher.name}")
        
        # Buscar todos os alunos sem professor
        students_without_teacher = Student.query.filter_by(teacher_id=None).all()
        
        print(f"\n👥 Alunos sem professor: {len(students_without_teacher)}")
        
        if not students_without_teacher:
            print("✅ Todos os alunos já têm professores associados!")
            return
        
        # Associar professores de forma aleatória
        updated_count = 0
        
        for student in students_without_teacher:
            # Escolher um professor aleatório
            random_teacher = random.choice(teachers)
            student.teacher_id = random_teacher.id
            updated_count += 1
            
            if updated_count % 50 == 0:
                print(f"   Processados: {updated_count} alunos...")
        
        try:
            db.session.commit()
            print(f"\n✅ {updated_count} alunos foram associados a professores com sucesso!")
            
            # Mostrar estatísticas
            print("\n📊 Distribuição por professor:")
            for teacher in teachers:
                count = Student.query.filter_by(teacher_id=teacher.id).count()
                print(f"   - {teacher.name}: {count} alunos")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao salvar no banco: {e}")

if __name__ == "__main__":
    print("🎯 Iniciando associação de professores aos alunos...")
    assign_teachers_to_students()
    print("🏁 Processo concluído!")