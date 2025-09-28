#!/usr/bin/env python3
"""
Script para recalcular os pontos CSA de todos os alunos
Agora que turma_meta foi corrigido, podemos calcular os pontos CSA
"""

from app import create_app
from models import Student, db
from listening_csa import compute_listening_csa

def recalculate_all_csa():
    """Recalcula os pontos CSA para todos os alunos"""
    
    # Criar contexto da aplicação
    app = create_app()
    if isinstance(app, tuple):
        app = app[0]
    
    with app.app_context():
        print("🔄 Iniciando recálculo de CSA para todos os alunos...")
        
        # Buscar todos os alunos com listening e turma_meta
        students = Student.query.filter(
            Student.listening.isnot(None),
            Student.turma_meta.isnot(None),
            Student.turma_meta != ''
        ).all()
        
        print(f"📊 Encontrados {len(students)} alunos para recálculo")
        
        updated_count = 0
        errors = 0
        
        for student in students:
            try:
                # Calcular CSA
                csa_result = compute_listening_csa(student.turma_meta, student.listening)
                old_points = student.listening_csa_points
                new_points = csa_result['points']
                
                student.listening_csa_points = new_points
                updated_count += 1
                
                if updated_count <= 10:  # Mostrar apenas os primeiros 10
                    print(f"✅ {student.name}: {old_points} → {new_points} (Turma: {student.turma_meta}, Listening: {student.listening})")
                elif updated_count == 11:
                    print("... (continuando recálculo para todos os alunos)")
                    
            except Exception as e:
                errors += 1
                print(f"❌ Erro ao calcular CSA para {student.name}: {e}")
        
        if updated_count > 0:
            try:
                db.session.commit()
                print(f"\n🎉 Recálculo concluído!")
                print(f"✅ {updated_count} alunos atualizados com sucesso")
                if errors > 0:
                    print(f"⚠️ {errors} erros encontrados")
                    
                # Verificar alguns resultados
                print("\n📊 Amostra dos resultados:")
                sample_students = Student.query.filter(
                    Student.listening_csa_points.isnot(None)
                ).limit(5).all()
                
                for student in sample_students:
                    print(f"   {student.name}: Listening={student.listening}, Turma={student.turma_meta}, CSA={student.listening_csa_points}")
                
            except Exception as e:
                db.session.rollback()
                print(f"❌ Erro ao salvar no banco: {e}")
        else:
            print("ℹ️ Nenhum aluno precisou ser atualizado")

if __name__ == "__main__":
    recalculate_all_csa()