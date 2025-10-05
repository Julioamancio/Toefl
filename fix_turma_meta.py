#!/usr/bin/env python3
"""
Script para corrigir o problema de turma_meta None
Migra os dados do meta_label das classes para o campo turma_meta dos alunos
"""

from app import create_app
from models import Student, db

def fix_turma_meta():
    """Corrige o turma_meta dos alunos baseado no meta_label da classe"""
    
    # Criar contexto da aplicação
    app = create_app()
    if isinstance(app, tuple):
        app = app[0]
    
    with app.app_context():
        print("🔄 Iniciando correção do turma_meta...")
        
        # Buscar alunos sem turma_meta
        students_without_meta = Student.query.filter(
            (Student.turma_meta.is_(None)) | (Student.turma_meta == '')
        ).all()
        
        print(f"📊 Encontrados {len(students_without_meta)} alunos sem turma_meta")
        
        migrated_count = 0
        errors = 0
        
        for student in students_without_meta:
            try:
                if student.class_info and student.class_info.meta_label:
                    old_meta = student.turma_meta
                    student.turma_meta = student.class_info.meta_label
                    migrated_count += 1
                    
                    print(f"✅ {student.name}: {old_meta} → {student.turma_meta}")
                else:
                    print(f"⚠️ {student.name}: Sem classe ou meta_label")
                    
            except Exception as e:
                errors += 1
                print(f"❌ Erro ao migrar {student.name}: {e}")
        
        if migrated_count > 0:
            try:
                db.session.commit()
                print(f"\n🎉 Migração concluída!")
                print(f"✅ {migrated_count} alunos migrados com sucesso")
                if errors > 0:
                    print(f"⚠️ {errors} erros encontrados")
                    
                # Verificar resultado
                remaining = Student.query.filter(
                    (Student.turma_meta.is_(None)) | (Student.turma_meta == '')
                ).count()
                print(f"📊 Alunos ainda sem turma_meta: {remaining}")
                
            except Exception as e:
                db.session.rollback()
                print(f"❌ Erro ao salvar no banco: {e}")
        else:
            print("ℹ️ Nenhum aluno precisou ser migrado")

if __name__ == "__main__":
    fix_turma_meta()