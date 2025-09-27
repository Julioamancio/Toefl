#!/usr/bin/env python3
"""
Script para recalcular listening_csa_points apenas para alunos que não têm pontuação
"""

from app import app
from models import db, Student
from listening_csa import compute_listening_csa

def recalculate_missing_csa():
    """Recalcula listening_csa_points apenas para alunos que não têm pontuação"""
    
    print("🔄 Iniciando recálculo de listening_csa_points para alunos sem pontuação...")
    
    # Buscar alunos sem listening_csa_points
    students_without_csa = Student.query.filter(Student.listening_csa_points.is_(None)).all()
    
    print(f"📊 Encontrados {len(students_without_csa)} alunos sem pontuação CSA")
    
    if not students_without_csa:
        print("✅ Todos os alunos já têm pontuação CSA calculada!")
        return
    
    updated_count = 0
    error_count = 0
    
    for i, student in enumerate(students_without_csa, 1):
        try:
            # Verificar se o aluno tem os dados necessários
            if student.listening is None:
                print(f"   ⚠️  {student.name} (ID: {student.id}): Sem score de listening")
                continue
                
            if not student.class_info or not student.class_info.meta_label:
                print(f"   ⚠️  {student.name} (ID: {student.id}): Sem rótulo escolar")
                continue
            
            # Calcular listening_csa_points
            rotulo_escolar = float(student.class_info.meta_label)
            csa_result = compute_listening_csa(rotulo_escolar, student.listening)
            
            # Atualizar o campo com os pontos CSA
            student.listening_csa_points = csa_result["points"]
            
            updated_count += 1
            
            # Log de progresso a cada 50 alunos
            if i % 50 == 0:
                print(f"   ✅ Processados {i}/{len(students_without_csa)} alunos...")
                
        except Exception as e:
            print(f"   ❌ Erro ao processar {student.name} (ID: {student.id}): {e}")
            error_count += 1
    
    try:
        # Commit das mudanças
        db.session.commit()
        print(f"\n✅ Recálculo concluído!")
        print(f"   • Alunos atualizados: {updated_count}")
        print(f"   • Erros: {error_count}")
        
        # Verificação final
        remaining_without_csa = Student.query.filter(Student.listening_csa_points.is_(None)).count()
        print(f"   • Alunos ainda sem CSA: {remaining_without_csa}")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao salvar no banco: {e}")

if __name__ == '__main__':
    with app.app_context():
        recalculate_missing_csa()